import paramiko
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed, ThreadPoolExecutor
from datetime import datetime
import logging
import re
import os
import sys
from typing import Dict, List, Optional, Tuple
import signal

class GracefulExit:
    """优雅退出处理"""
    def __init__(self):
        self.exit_flag = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
    
    def exit_gracefully(self, signum, frame):
        self.exit_flag = True
        print("\n🛑 接收到退出信号，正在优雅退出...")

class NetworkDeviceChecker:
    def __init__(self, config: Dict = None):
        # 默认配置
        default_config = {
            'ssh_timeout': 15,           # SSH连接超时
            'cmd_timeout': 15,           # 命令执行超时
            'max_workers': 10,           # 最大并发数（生产环境调低）
            'readonly_mode': True,       # 只读模式
            'test_mode': False,          # 测试模式
            'max_test_devices': 3,       # 测试模式最大设备数
            'rate_limit_delay': 0.5,     # 命令间延迟（秒）
            'safe_disconnect': True,     # 安全断开连接
            'enable_logging': True,      # 启用详细日志
            'log_file': 'network_checker.log'
        }
        
        self.config = {**default_config, **(config or {})}
        self.exit_handler = GracefulExit()
        
        # 初始化日志
        self._setup_logging()
        
        # 危险命令列表（只读模式下会警告）
        self.dangerous_commands = [
            'system-view', 'configure', 'write', 'save', 'reboot',
            'reset', 'delete', 'format', 'shutdown', 'undo', 'clear'
        ]
        
        # 只读命令白名单
        self.readonly_whitelist = [
            'display', 'show', 'dir', 'ping', 'tracert', 'telnet',
            'ssh', 'ifconfig', 'ipconfig', 'netstat', 'ip route'
        ]
        
        logging.info(f"网络设备检查器初始化完成，配置: {self.config}")
    
    def _setup_logging(self):
        """配置日志系统"""
        log_level = logging.DEBUG if self.config['enable_logging'] else logging.INFO
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['log_file'], encoding='utf-8'),
                logging.StreamHandler(sys.stdout)  # 同时输出到控制台
            ]
        )
        
        # 降低paramiko日志级别
        logging.getLogger("paramiko").setLevel(logging.WARNING)
    
    def validate_command(self, command: str) -> Tuple[bool, str]:
        """验证命令安全性"""
        cmd_lower = command.lower().strip()
        
        if self.config['readonly_mode']:
            # 检查是否包含危险命令
            for dangerous in self.dangerous_commands:
                if dangerous in cmd_lower:
                    return False, f"危险命令: {dangerous}"
            
            # 检查是否是只读命令
            is_readonly = any(cmd in cmd_lower for cmd in self.readonly_whitelist)
            if not is_readonly:
                logging.warning(f"未知命令类型: {command}")
                # 如果严格模式，可以返回False
        
        return True, "命令安全"
    
    def safe_execute_command(self, channel, command: str, device_ip: str = "") -> str:
        """安全执行命令并返回结果"""
        
        # 检查退出标志
        if self.exit_handler.exit_flag:
            logging.info(f"退出标志已设置，跳过命令执行: {command}")
            return ""
        
        # 验证命令
        is_safe, reason = self.validate_command(command)
        if not is_safe:
            logging.error(f"命令验证失败: {command}, 原因: {reason}")
            if self.config['readonly_mode']:
                return f"ERROR: {reason}"
        
        try:
            logging.debug(f"[{device_ip}] 执行命令: {command}")
            
            # 发送命令
            channel.send(command + '\n')
            time.sleep(self.config['rate_limit_delay'])
            
            # 等待并读取输出
            output = ''
            start_time = time.time()
            max_wait = self.config['cmd_timeout']
            
            while time.time() - start_time < max_wait:
                if channel.recv_ready():
                    chunk = channel.recv(65535).decode('utf-8', errors='ignore')
                    output += chunk
                    
                    # 检查是否返回命令行提示符
                    if self._is_command_prompt(chunk):
                        break
                    
                    # 处理分页
                    if self._has_more_prompt(chunk):
                        channel.send(' ')
                        time.sleep(0.3)
                
                # 检查退出标志
                if self.exit_handler.exit_flag:
                    logging.info(f"退出标志已设置，中断命令执行")
                    break
                    
                time.sleep(0.1)
            
            # 清理输出
            cleaned = self._clean_output(output, command, device_ip)
            return cleaned
            
        except Exception as e:
            logging.error(f"[{device_ip}] 命令执行异常: {command}, 错误: {e}")
            return f"ERROR: {str(e)}"
    
    def _is_command_prompt(self, text: str) -> bool:
        """检查是否为命令行提示符"""
        patterns = [
            r'[>\]#]\s*$',      # >, ], # 结尾
            r'[a-zA-Z0-9\-_]+[>#]\s*$',  # hostname> 或 hostname#
            r'\]\s*$'           # Huawei/Cisco的]提示符
        ]
        
        lines = text.strip().split('\n')
        if not lines:
            return False
        
        last_line = lines[-1].strip()
        for pattern in patterns:
            if re.search(pattern, last_line):
                return True
        return False
    
    def _has_more_prompt(self, text: str) -> bool:
        """检查是否有分页提示"""
        more_patterns = [
            '---- More ----',
            '--More--',
            'Press any key to continue',
            '---(more)---'
        ]
        return any(pattern in text for pattern in more_patterns)
    
    def _clean_output(self, output: str, command: str, device_ip: str) -> str:
        """清理命令输出"""
        if not output:
            return ""
        
        lines = output.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # 跳过空行
            if not stripped:
                continue
            
            # 跳过命令回显
            if command.strip() in stripped:
                continue
            
            # 跳过分页符和提示符
            if self._has_more_prompt(stripped):
                continue
            
            # 跳过命令行提示符
            if self._is_command_prompt(stripped):
                continue
            
            cleaned_lines.append(stripped)
        
        result = '\n'.join(cleaned_lines)
        logging.debug(f"[{device_ip}] 命令输出清理完成，原始长度: {len(output)}, 清理后: {len(result)}")
        return result
    
    def safe_connect(self, device_info: Dict) -> Optional[paramiko.SSHClient]:
        """安全建立SSH连接"""
        ip = device_info['ip']
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.WarningPolicy())  # 比AutoAddPolicy更安全
            
            # 设置连接超时
            connect_kwargs = {
                'hostname': ip,
                'username': device_info['username'],
                'password': device_info['password'],
                'timeout': self.config['ssh_timeout'],
                'banner_timeout': 10,
                'look_for_keys': False,
                'allow_agent': False
            }
            
            # 可选: 如果有密钥文件
            if 'key_file' in device_info:
                connect_kwargs['key_filename'] = device_info['key_file']
                connect_kwargs['look_for_keys'] = True
            
            logging.info(f"正在连接设备: {ip}")
            ssh.connect(**connect_kwargs)
            logging.info(f"成功连接设备: {ip}")
            
            return ssh
            
        except paramiko.AuthenticationException:
            logging.error(f"[{ip}] 认证失败")
        except paramiko.SSHException as e:
            logging.error(f"[{ip}] SSH连接异常: {e}")
        except Exception as e:
            logging.error(f"[{ip}] 连接失败: {e}")
        
        return None
    
    def safe_disconnect(self, ssh: paramiko.SSHClient, channel=None, device_ip: str = ""):
        """安全断开SSH连接"""
        if not ssh or not self.config['safe_disconnect']:
            return
        
        try:
            # 如果有通道，先尝试发送退出命令
            if channel:
                try:
                    channel.send('quit\n')
                    time.sleep(0.5)
                except:
                    pass
            
            # 关闭连接
            ssh.close()
            logging.debug(f"[{device_ip}] 安全断开连接")
            
        except Exception as e:
            logging.warning(f"[{device_ip}] 断开连接时异常: {e}")
    
    def check_device_ntp(self, device_info: Dict, custom_cmd: str = None) -> Dict:
        """检查单台设备的NTP配置"""
        ip = device_info['ip']
        vendor = device_info.get('vendor', 'unknown').lower()
        
        result = {
            'ip': ip,
            'vendor': vendor,
            'has_ntp': False,
            'has_custom': False if custom_cmd else None,
            'status': 'failed',
            'error': '',
            'ntp_config': '',
            'custom_output': '' if custom_cmd else None,
            'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        ssh = None
        channel = None
        
        try:
            # 检查退出标志
            if self.exit_handler.exit_flag:
                result['error'] = "脚本被中断"
                return result
            
            # 安全连接
            ssh = self.safe_connect(device_info)
            if not ssh:
                result['error'] = "连接失败"
                return result
            
            # 创建交互式Shell
            channel = ssh.invoke_shell()
            channel.settimeout(self.config['cmd_timeout'])
            
            # 等待欢迎信息
            time.sleep(1)
            channel.recv(65535)
            
            # 进入系统视图（仅Huawei设备）
            if vendor == 'huawei':
                logging.debug(f"[{ip}] 进入系统视图")
                channel.send('system-view\n')
                time.sleep(1)
                channel.recv(65535)
            
            # 检查NTP配置
            ntp_command = 'display current-configuration | include ntp'
            ntp_output = self.safe_execute_command(channel, ntp_command, ip)
            result['ntp_config'] = ntp_output
            
            # 精确判断NTP配置
            if ntp_output and 'ntp' in ntp_output.lower():
                # 进一步过滤，排除注释和无效行
                ntp_lines = [line for line in ntp_output.split('\n') 
                           if 'ntp' in line.lower() and not line.strip().startswith('#')]
                result['has_ntp'] = len(ntp_lines) > 0
            else:
                result['has_ntp'] = False
            
            # 检查自定义命令
            if custom_cmd:
                custom_output = self.safe_execute_command(channel, custom_cmd, ip)
                result['custom_output'] = custom_output
                result['has_custom'] = bool(custom_output)
            
            # 退出系统视图（如果进入过）
            if vendor == 'huawei':
                channel.send('return\n')
                time.sleep(0.5)
            
            result['status'] = 'success'
            logging.info(f"[{ip}] 检查完成，NTP: {result['has_ntp']}")
            
        except Exception as e:
            result['error'] = str(e)
            logging.error(f"[{ip}] 检查过程中异常: {e}")
            
        finally:
            # 安全断开连接
            self.safe_disconnect(ssh, channel, ip)
        
        return result

def main():
    """主函数"""
    
    # 配置文件
    CONFIG = {
        'test_mode': False,           # 生产环境设为False
        'max_workers': 8,            # 生产环境建议5-10
        'readonly_mode': True,       # 确保只读
        'enable_logging': True,      # 生产环境建议True
        'log_file': f'network_check_{datetime.now().strftime("%Y%m%d_%H%M")}.log'
    }
    
    INPUT_FILE = 'devices.csv'
    OUTPUT_FILE = f'no_config_devices_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    REPORT_FILE = f'check_report_{datetime.now().strftime("%Y%m%d_%H%M")}.txt'
    
    print("=" * 70)
    print("📡 网络设备NTP配置检查工具")
    print("=" * 70)
    
    if CONFIG['test_mode']:
        print("⚠️  警告: 运行在测试模式")
    
    print(f"📁 输入文件: {INPUT_FILE}")
    print(f"📊 输出文件: {OUTPUT_FILE}")
    print(f"📝 报告文件: {REPORT_FILE}")
    print(f"⚡ 最大并发数: {CONFIG['max_workers']}")
    print("=" * 70 + "\n")
    
    # 检查输入文件
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 错误: 找不到输入文件 {INPUT_FILE}")
        sys.exit(1)
    
    try:
        print("📖 读取设备清单...")
        df = pd.read_csv(INPUT_FILE, encoding='utf-8')
        
        if CONFIG['test_mode']:
            print(f"🧪 测试模式: 仅检查前{CONFIG.get('max_test_devices', 3)}台设备")
            df = df.head(CONFIG.get('max_test_devices', 3))
        
        print(f"📋 总设备数: {len(df)}")
        
        # 初始化检查器
        checker = NetworkDeviceChecker(CONFIG)
        
        # 存储结果
        all_results = []
        no_config_devices = []
        
        print(f"\n🚀 开始并发检查，线程数: {CONFIG['max_workers']}")
        print("-" * 70)
        
        # 使用线程池
        with ThreadPoolExecutor(max_workers=CONFIG['max_workers']) as executor:
            # 提交所有任务
            future_to_device = {}
            for _, row in df.iterrows():
                if checker.exit_handler.exit_flag:
                    print("\n🛑 检测到退出信号，停止提交新任务")
                    break
                
                device_ip = row['ip']
                future = executor.submit(checker.check_device_ntp, row.to_dict())
                future_to_device[future] = device_ip
            
            # 处理完成的任务
            completed = 0
            total = len(future_to_device)
            
            for future in as_completed(future_to_device):
                if checker.exit_handler.exit_flag:
                    print("\n🛑 检测到退出信号，停止处理结果")
                    break
                
                ip = future_to_device[future]
                completed += 1
                
                try:
                    result = future.result(timeout=300)  # 5分钟超时
                    all_results.append(result)
                    
                    # 显示进度
                    status_icon = "✅" if result['status'] == 'success' else "❌"
                    ntp_status = "已配置" if result['has_ntp'] else "未配置"
                    
                    print(f"[{completed}/{total}] {status_icon} {ip:15} "
                          f"状态: {result['status']:8} NTP: {ntp_status}")
                    
                    # 记录不符合要求的设备
                    if result['status'] == 'success' and not result['has_ntp']:
                        no_config_devices.append({
                            'ip': result['ip'],
                            'vendor': result['vendor'],
                            'reason': "缺少NTP配置",
                            'error': result['error']
                        })
                    elif result['status'] != 'success':
                        no_config_devices.append({
                            'ip': result['ip'],
                            'vendor': result['vendor'],
                            'reason': f"检查失败",
                            'error': result['error']
                        })
                        
                except Exception as e:
                    logging.error(f"处理设备 {ip} 时异常: {e}")
                    print(f"[{completed}/{total}] ⚠️  {ip:15} 处理异常: {e}")
        
        print("\n" + "=" * 70)
        
        # 生成统计报告
        success_count = sum(1 for r in all_results if r['status'] == 'success')
        ntp_configured = sum(1 for r in all_results if r.get('has_ntp'))
        
        print(f"📊 检查完成！")
        print(f"   🔹 总设备数: {len(all_results)}")
        print(f"   🔹 成功检查: {success_count}")
        print(f"   🔹 NTP已配置: {ntp_configured}")
        print(f"   🔹 NTP未配置: {len(no_config_devices)}")
        print("=" * 70)
        
        # 保存详细结果到CSV
        if all_results:
            result_df = pd.DataFrame(all_results)
            result_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
            print(f"\n💾 详细结果已保存到: {OUTPUT_FILE}")
        
        # 保存报告文件
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("网络设备NTP配置检查报告\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"设备总数: {len(all_results)}\n")
            f.write(f"成功检查: {success_count}\n")
            f.write(f"NTP已配置: {ntp_configured}\n")
            f.write(f"NTP未配置: {len(no_config_devices)}\n")
            f.write("\n" + "=" * 60 + "\n")
            
            if no_config_devices:
                f.write("\n❌ 不符合要求的设备列表:\n")
                f.write("-" * 60 + "\n")
                for dev in no_config_devices:
                    f.write(f"IP: {dev['ip']:<15} | 厂商: {dev['vendor']:<8} | "
                           f"原因: {dev['reason']:<15} | 错误: {dev['error'][:50]}\n")
            else:
                f.write("\n✅ 所有设备都配置了NTP！\n")
        
        print(f"\n📄 检查报告已保存到: {REPORT_FILE}")
        
        # 显示不符合要求的设备
        if no_config_devices:
            print("\n❌ 不符合要求的设备:")
            print("-" * 60)
            for dev in no_config_devices[:20]:  # 最多显示20台
                print(f"  {dev['ip']:15} ({dev['vendor']:8}) - {dev['reason']}")
            if len(no_config_devices) > 20:
                print(f"  ... 还有 {len(no_config_devices) - 20} 台设备未显示")
        
        print(f"\n🎉 任务完成！详细日志请查看: {CONFIG['log_file']}")
        
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断执行")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序执行异常: {e}")
        logging.exception("程序执行异常")
        sys.exit(1)

if __name__ == '__main__':
    main()