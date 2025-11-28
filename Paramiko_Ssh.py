#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H3C 批量命令工具（单表并发版）
优化：单表维护 + 并发执行
打包：pyinstaller -F -c h3c_batch.py
"""
import paramiko, logging, argparse, csv, re, socket, time, json, sys, os
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed  # 新增并发库

LOG_DIR = Path('logs')
RESULT_DIR = Path('results')
LOG_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

# ---------------- 配置参数 ----------------
MAX_WORKERS = 5  # 并发线程数，可根据电脑性能调整

# ---------------- 日志：屏幕 + 文件 ----------------
def setup_logger(ip: str):
    logfile = LOG_DIR / f"{ip}_{datetime.now():%Y%m%d_%H%M%S}.log"  # 加时间戳避免重复
    logger = logging.getLogger(ip)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
    
    # 控制台
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    
    # 文件
    fh = logging.FileHandler(logfile, encoding='utf-8')
    fh.setFormatter(fmt)
    
    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger

# ---------------- SSH 连接 ----------------
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

# ---------------- 执行命令 ----------------
PROMPT = re.compile(r'<[\w-]+>|\[[\w-]+\]')

def run_cmds_shell(ssh, cmds, logger):
    chan = ssh.invoke_shell()
    chan.settimeout(15)  # 增加超时时间
    time.sleep(0.5)
    chan.recv(65535)  # 清空初始输出
    
    # 发送屏幕长度设置
    chan.send('screen-length disable\n')
    time.sleep(0.5)
    chan.recv(65535)
    
    outputs = []
    for cmd in cmds:
        if not cmd.strip():
            continue
            
        chan.send(cmd + '\n')
        time.sleep(0.5)  # 命令间间隔
        
        buff = ''
        start_time = time.time()
        while time.time() - start_time < 10:  # 单命令超时10秒
            if chan.recv_ready():
                chunk = chan.recv(4096).decode('utf-8', errors='ignore')
                buff += chunk
                if PROMPT.search(buff.splitlines()[-1]) if buff.splitlines() else False:
                    break
            time.sleep(0.1)
        else:
            logger.warning(f"命令超时: {cmd}")
        
        # 清理输出：去除命令回显和最后提示符
        lines = buff.splitlines()
        if len(lines) > 1:
            clean_output = '\n'.join(lines[1:])  # 去除命令回显
            # 去除最后一行提示符
            if PROMPT.search(clean_output.splitlines()[-1]) if clean_output.splitlines() else False:
                clean_output = '\n'.join(clean_output.splitlines()[:-1])
        else:
            clean_output = buff
            
        outputs.append({'cmd': cmd, 'output': clean_output})
        logger.info('CMD: %s => %d chars', cmd, len(clean_output))
    
    chan.close()
    return outputs

# ---------------- 单台设备处理 ----------------
def run_device(device_info, cmds):
    """处理单台设备 - 修改为接收设备字典"""
    ip = device_info['ip']
    user = device_info['user']
    pwd = device_info['pwd']
    
    logger = setup_logger(ip)
    logger.info(f"开始处理设备 {ip}")
    
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
    """读取单表清单 - 新功能"""
    devices = []
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 验证必要字段
            if 'ip' in row and 'user' in row and 'pwd' in row:
                devices.append({
                    'ip': row['ip'].strip(),
                    'user': row['user'].strip(),
                    'pwd': row['pwd'].strip()
                })
            else:
                print(f"!! 跳过无效行: {row}")
    return devices

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

# ---------------- 交互式文件选择 ----------------
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

# ---------------- 主函数 - 新增并发 ----------------
def main():
    print('=' * 60)
    print('H3C 批量命令工具（单表并发版）')
    print('=' * 60)

    # 只需要一个设备清单文件
    inventory_file = ask_file('请输入设备清单文件', 'inventory.csv')
    cmd_file = ask_file('请输入命令文件', 'commands.txt')

    # 读取单表设备清单
    devices = read_single_inventory(inventory_file)
    if not devices:
        sys.exit('没有找到有效的设备配置')
    
    print(f"找到 {len(devices)} 台设备")
    
    # 读取命令
    cmds = [l.strip() for l in open(cmd_file, encoding='utf-8') if l.strip()]
    if not cmds:
        sys.exit('命令文件为空')
    
    print(f"加载 {len(cmds)} 条命令")
    print(f"使用 {MAX_WORKERS} 个并发线程")
    print("开始执行...\n")

    results = []
    
    # 使用线程池并发执行
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        future_to_device = {
            executor.submit(run_device, device, cmds): device 
            for device in devices
        }
        
        # 收集结果
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

    write_report(results)
    
    # 统计结果
    success_count = sum(1 for r in results if r['success'])
    print(f"\n执行完成: 成功 {success_count}/{len(devices)} 台设备")
    
    input('\n按回车退出...')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n用户中断')
    except Exception as e:
        print(f'\n程序异常: {e}')
    finally:
        # 确保程序不会立即退出
        try:
            input('按回车退出...')
        except:
            pass