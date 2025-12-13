# ...existing code...
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H3C 批量命令工具（单表并发版 + 邮件报告）
主文件：保持为你主要查看的入口，邮件和检查逻辑拆到独立模块
"""
from check_paramiko import NetworkDeviceChecker
from email_utils import send_email, ask_email_config
import paramiko, logging, argparse, csv, re, socket, time, json, sys, os
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

LOG_DIR = Path('logs')
RESULT_DIR = Path('results')
CONFIG_FILE = Path('config.json')
LOG_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

# ---------------- 配置参数 ----------------
MAX_WORKERS = 5  # 并发线程数

# ---------------- 邮箱服务映射（保留在主文件只是引用） ----------------
MAIL_CONFIGS = {
    'qq': {'smtp': 'smtp.qq.com', 'port': 465},
    '163': {'smtp': 'smtp.163.com', 'port': 465},
    '126': {'smtp': 'smtp.126.com', 'port': 465},
    'sina': {'smtp': 'smtp.sina.com', 'port': 465},
    'aliyun': {'smtp': 'smtp.aliyun.com', 'port': 465}
}

# ---------------- 配置管理 ----------------
class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        'mail': {
            'enabled': True,
            'type': 'qq',
            'sender': '1132634029@qq.com',
            'password': 'tchjfajfgsuehcah',
            'receivers': ['1132634029@qq.com'],
            'subject_prefix': 'H3C批量命令执行报告'
        },
        'ssh': {
            'timeout': 10,
            'port': 22
        },
        'execution': {
            'max_workers': 5,
            'command_timeout': 10
        }
    }
    
    @staticmethod
    def load_config():
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                config = ConfigManager.DEFAULT_CONFIG.copy()
                ConfigManager._deep_update(config, user_config)
                print(f"✓ 加载配置文件: {CONFIG_FILE}")
                return config
            except Exception as e:
                print(f"⚠ 配置文件读取失败，使用默认配置: {e}")
        else:
            print("ℹ 未找到配置文件，使用默认配置")
        return ConfigManager.DEFAULT_CONFIG.copy()
    
    @staticmethod
    def save_config(config):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"✓ 配置文件已保存: {CONFIG_FILE}")
            return True
        except Exception as e:
            print(f"✗ 配置文件保存失败: {e}")
            return False
    
    @staticmethod
    def create_default_config():
        return ConfigManager.save_config(ConfigManager.DEFAULT_CONFIG)
    
    @staticmethod
    def _deep_update(base_dict, update_dict):
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                ConfigManager._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

# ---------------- 日志 ----------------
def setup_logger(ip: str):
    logfile = LOG_DIR / f"{ip}_{datetime.now():%Y%m%d_%H%M%S}.log"
    logger = logging.getLogger(ip)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    fh = logging.FileHandler(logfile, encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger

# ---------------- SSH连接（保留回退实现） ----------------
def connect(ip, user, pwd, port=22, timeout=10):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(ip, port=port, username=user, password=pwd,
                    timeout=timeout, auth_timeout=5,
                    look_for_keys=False, allow_agent=False)
        return ssh, None
    except paramiko.AuthenticationException:
        return None, "认证失败"
    except socket.timeout:
        return None, "连接超时"
    except Exception as e:
        return None, f"连接异常: {str(e)}"

# ---------------- 执行命令（回退实现） ----------------
PROMPT = re.compile(r'<[\w-]+>|\[[\w-]+\]')

def run_cmds_shell(ssh, cmds, logger):
    chan = ssh.invoke_shell()
    chan.settimeout(15)
    time.sleep(0.5)
    try:
        chan.recv(65535)
    except Exception:
        pass
    
    chan.send('screen-length disable\n')
    time.sleep(0.5)
    try:
        chan.recv(65535)
    except Exception:
        pass
    
    outputs = []
    for cmd in cmds:
        if not cmd.strip():
            continue
        chan.send(cmd + '\n')
        time.sleep(0.5)
        
        buff = ''
        start_time = time.time()
        while time.time() - start_time < 10:
            if chan.recv_ready():
                chunk = chan.recv(4096).decode('utf-8', errors='ignore')
                buff += chunk
                if PROMPT.search(buff.splitlines()[-1]) if buff.splitlines() else False:
                    break
            time.sleep(0.1)
        else:
            logger.warning(f"命令超时: {cmd}")
        
        lines = buff.splitlines()
        if len(lines) > 1:
            clean_output = '\n'.join(lines[1:])
            if PROMPT.search(clean_output.splitlines()[-1]) if clean_output.splitlines() else False:
                clean_output = '\n'.join(clean_output.splitlines()[:-1])
        else:
            clean_output = buff
            
        outputs.append({'cmd': cmd, 'output': clean_output})
        logger.info('CMD: %s => %d chars', cmd, len(clean_output))
    
    try:
        chan.close()
    except Exception:
        pass
    return outputs

# ---------------- 单台设备处理（优先使用 checker） ----------------
def run_device(device_info, cmds, checker=None):
    ip = device_info['ip']
    user = device_info['user']
    pwd = device_info['pwd']
    
    logger = setup_logger(ip)
    logger.info(f"开始处理设备 {ip}")
    
    # 优先使用 checker 提供的安全连接/执行/断开接口
    if checker:
        ssh = checker.safe_connect({'ip': ip, 'username': user, 'password': pwd})
        if not ssh:
            logger.error('连接失败（checker）')
            return {'ip': ip, 'success': False, 'error': '连接失败（checker）'}
        channel = None
        try:
            channel = ssh.invoke_shell()
            try:
                channel.settimeout(checker.config.get('cmd_timeout', 15))
            except Exception:
                channel.settimeout(15)
            time.sleep(1)
            try:
                channel.recv(65535)
            except Exception:
                pass
            
            outputs = []
            for cmd in cmds:
                if not cmd.strip():
                    continue
                out = checker.safe_execute_command(channel, cmd, ip)
                outputs.append({'cmd': cmd, 'output': out})
                logger.info('CMD: %s => %d chars', cmd, len(out))
            
            logger.info('所有命令执行完成')
            return {'ip': ip, 'success': True, 'outputs': outputs}
        except Exception as e:
            logger.error('执行过程异常: %s', str(e))
            return {'ip': ip, 'success': False, 'error': str(e)}
        finally:
            try:
                checker.safe_disconnect(ssh, channel, ip)
            except Exception:
                try:
                    ssh.close()
                except Exception:
                    pass
    else:
        # 回退到原有实现
        ssh, err = connect(ip, user, pwd)
        if err:
            logger.error('连接失败: %s', err)
            return {'ip': ip, 'success': False, 'error': err}
        
        try:
            outs = run_cmds_shell(ssh, cmds, logger)
            logger.info('所有命令执行完成')
            return {'ip': ip, 'success': True, 'outputs': outs}
        except Exception as e:
            logger.error('执行过程异常: %s', str(e))
            return {'ip': ip, 'success': False, 'error': str(e)}
        finally:
            try:
                ssh.close()
            except:
                pass

# ---------------- 文件操作 ----------------
def read_single_inventory(path):
    devices = []
    receivers_from_inventory = []
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'ip' in row and 'user' in row and 'pwd' in row:
                devices.append({
                    'ip': row['ip'].strip(),
                    'user': row['user'].strip(),
                    'pwd': row['pwd'].strip()
                })
            if 'email' in row and row['email'].strip():
                receivers_from_inventory.append(row['email'].strip())
            else:
                print(f"!! 跳过无效行: {row}")
    return devices, receivers_from_inventory

def write_report(allres):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = RESULT_DIR / f'results_{ts}.csv'
    json_path = csv_path.with_suffix('.json')
    csv_rows = [['IP', 'Command', 'Success', 'OutputLen', 'Output']]
    for dev in allres:
        ip = dev['ip']
        if not dev['success']:
            csv_rows.append([ip, '', 'FAIL', '', dev.get('error', '未知错误')])
            continue
        for o in dev['outputs']:
            output_preview = o['output'][:200] + '...' if len(o['output']) > 200 else o['output']
            csv_rows.append([ip, o['cmd'], 'OK', len(o['output']), output_preview])
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerows(csv_rows)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(allres, f, ensure_ascii=False, indent=2)
    print(f'\n报告文件: {csv_path}')
    print(f'详细数据: {json_path}')
    return csv_path, json_path

# ---------------- 文件选择 ----------------
def ask_file(prompt, default_file):
    try:
        path = input(f'{prompt} (默认: {default_file}) > ').strip().strip('"')
    except KeyboardInterrupt:
        sys.exit('用户取消')
    if not path:
        path = default_file
    if not Path(path).exists():
        sys.exit(f'文件不存在: {path}')
    return Path(path)

# ---------------- 主函数 ----------------
def main():
    print('=' * 60)
    print('H3C 批量命令工具（配置文件版）')
    print('=' * 60)
    
    config = ConfigManager.load_config()
    mail_config = config['mail']
    
    print(f"\n当前邮件配置:")
    print(f"  发件人: {mail_config['sender']}")
    print(f"  收件人: {', '.join(mail_config['receivers'])}")
    print(f"  邮箱类型: {mail_config['type']}")
    
    if not CONFIG_FILE.exists():
        create = input("\n是否创建配置文件 config.json？(y/n): ").strip().lower()
        if create == 'y':
            ConfigManager.create_default_config()
    
    inventory_file = ask_file('请输入设备清单文件', 'inventory.csv')
    cmd_file = ask_file('请输入命令文件', 'commands.txt')

    devices, receivers_from_inventory = read_single_inventory(inventory_file)
    if not devices:
        sys.exit('没有找到有效的设备配置')
    
    print(f"找到 {len(devices)} 台设备")
    if receivers_from_inventory:
        print(f"从清单中读取到 {len(receivers_from_inventory)} 个收件人")
        all_receivers = list(set(mail_config['receivers'] + receivers_from_inventory))
        mail_config['receivers'] = all_receivers
        print(f"合并后收件人: {', '.join(all_receivers)}")
    
    cmds = [l.strip() for l in open(cmd_file, encoding='utf-8') if l.strip()]
    if not cmds:
        sys.exit('命令文件为空')
    
    print(f"加载 {len(cmds)} 条命令")
    print(f"使用 {config['execution']['max_workers']} 个并发线程")
    print("开始执行...\n")

    results = []

    # 创建 checker（使用 check_paramiko 的实现）
    checker = NetworkDeviceChecker({
        'ssh_timeout': config['ssh']['timeout'],
        'cmd_timeout': config['execution']['command_timeout'],
        'max_workers': config['execution']['max_workers'],
        'rate_limit_delay': 0.5,
        'readonly_mode': True,
        'enable_logging': False
    })

    with ThreadPoolExecutor(max_workers=config['execution']['max_workers']) as executor:
        future_to_device = {
            executor.submit(run_device, device, cmds, checker): device
            for device in devices
        }
        
        for future in as_completed(future_to_device):
            device = future_to_device[future]
            try:
                result = future.result()
                results.append(result)
                status = "成功" if result['success'] else "失败"
                print(f">>> {device['ip']} 执行{status}")
            except Exception as exc:
                print(f">>> {device['ip']} 生成异常: {exc}")
                results.append({
                    'ip': device['ip'],
                    'success': False,
                    'error': f'执行异常: {str(exc)}'
                })

    csv_path, json_path = write_report(results)
    
    success_count = sum(1 for r in results if r['success'])
    fail_count = len(devices) - success_count
    print(f"\n执行完成: 成功 {success_count}/{len(devices)} 台设备")
    
    if mail_config.get('enabled', True):
        send_mail = input("\n是否发送邮件报告？(y/n, 回车默认发送): ").strip().lower()
        if send_mail == '' or send_mail == 'y':
            mail_config = ask_email_config(mail_config)
            subject = f"{mail_config.get('subject_prefix', 'H3C批量命令执行报告')} - {datetime.now():%Y-%m-%d %H:%M:%S}"
            content = f"""H3C网络设备批量命令执行报告

执行时间: {datetime.now():%Y-%m-%d %H:%M:%S}
设备总数: {len(devices)}
成功设备: {success_count}
失败设备: {fail_count}
命令数量: {len(cmds)}

统计信息:
成功设备列表: {', '.join([r['ip'] for r in results if r['success']]) or '无'}
失败设备列表: {', '.join([r['ip'] for r in results if not r['success']]) or '无'}

详细执行结果请查看附件。
"""
            success = send_email(
                email_type=mail_config['type'],
                sender=mail_config['sender'],
                password=mail_config['password'],
                receivers=mail_config['receivers'],
                subject=subject,
                content=content,
                attachments=[str(csv_path), str(json_path)]
            )
            if success:
                print("邮件报告已发送！")
            else:
                print("邮件发送失败，请检查配置")
    else:
        print("邮件功能已禁用")
    
    save_config = input("\n是否保存当前邮件配置？(y/n): ").strip().lower()
    if save_config == 'y':
        config['mail'] = mail_config
        ConfigManager.save_config(config)
    
    print("\n程序执行完成！")
    input('按回车退出...')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n用户中断')
    except Exception as e:
        print(f'\n程序异常: {e}')
        input('按回车退出...')