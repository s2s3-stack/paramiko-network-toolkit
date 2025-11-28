#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H3C 批量命令工具（拖拽/交互版）
打包：pyinstaller -F -c h3c_batch.py
"""
import paramiko, logging, argparse, csv, re, socket, time, json, sys, os
from pathlib import Path
from datetime import datetime

LOG_DIR = Path('logs')
RESULT_DIR = Path('results')
LOG_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

# ---------------- 日志：屏幕 + 文件 ----------------
def setup_logger(ip: str):
    logfile = LOG_DIR / f"{ip}_{datetime.now():%Y%m%d}.log"
    logger = logging.getLogger(ip)
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
        return None, "认证失败，用户名或密码错误"
    except socket.timeout:
        return None, "网络连接超时"
    except Exception as e:
        return None, str(e)

# ---------------- 执行命令 ----------------
PROMPT = re.compile(r'<[\w-]+>|\[[\w-]+\]')

def run_cmds_shell(ssh, cmds, logger):
    chan = ssh.invoke_shell()
    chan.settimeout(10)
    chan.send('screen-length disable\n')
    time.sleep(0.5)
    chan.recv(65535)
    outputs = []
    for cmd in cmds:
        chan.send(cmd + '\n')
        buff = ''
        while True:
            chunk = chan.recv(4096).decode('utf-8', errors='ignore')
            buff += chunk
            if PROMPT.search(buff.splitlines()[-1]):
                break
        out = '\n'.join(buff.splitlines()[1:-1])
        outputs.append({'cmd': cmd, 'output': out})
        logger.info('CMD: %s => %d chars', cmd, len(out))
    chan.close()
    return outputs

# ---------------- 单台设备 ----------------
def run_device(ip, user, pwd, cmds):
    logger = setup_logger(ip)
    ssh, err = connect(ip, user, pwd)
    if err:
        logger.error('connect failed: %s', err)
        return {'ip': ip, 'success': False, 'error': err}
    try:
        outs = run_cmds_shell(ssh, cmds, logger)
        logger.info('all cmds done')
        return {'ip': ip, 'success': True, 'outputs': outs}
    finally:
        ssh.close()

# ---------------- 读写文件 ----------------
def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def write_report(allres):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = RESULT_DIR / f'results_{ts}.csv'
    json_path = csv_path.with_suffix('.json')
    csv_rows = [['IP', 'Command', 'Success', 'OutputLen', 'Output']]
    for dev in allres:
        ip = dev['ip']
        if not dev['success']:
            csv_rows.append([ip, '', 'FAIL', '', dev['error']])
            continue
        for o in dev['outputs']:
            csv_rows.append([ip, o['cmd'], 'OK', len(o['output']),
                             o['output'][:200] + '...'])
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerows(csv_rows)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(allres, f, ensure_ascii=False, indent=2)
    print(f'\nReport -> {csv_path}  {json_path}')

# ---------------- 交互式获取文件 ----------------
def ask_file(prompt, default_file):
    """
    支持拖拽/手动输入：
    1. 直接把文件拖进窗口，路径会自动填入；
    2. 直接回车使用默认值；
    3. 手动输入相对/绝对路径。
    """
    try:
        path = input(f'{prompt} (默认: {default_file}) > ').strip().strip('"')
    except KeyboardInterrupt:
        sys.exit('用户取消')
    if not path:
        path = default_file
    if not Path(path).exists():
        sys.exit(f'文件不存在: {path}')
    return Path(path)

# ---------------- main ----------------
def main():
    print('=' * 60)
    print('H3C 批量命令工具（交互/拖拽版）')
    print('打包命令: pyinstaller -F -c h3c_batch.py')
    print('=' * 60)

    inventory_file = ask_file('请输入设备清单', 'inventory.csv')
    cred_file = ask_file('请输入账号文件', 'credentials.csv')
    cmd_file = ask_file('请输入命令文件', 'commands.txt')

    devices = read_csv(inventory_file)
    creds = {c['ip']: c for c in read_csv(cred_file)}
    cmds = [l.strip() for l in open(cmd_file, encoding='utf-8') if l.strip()]

    results = []
    for d in devices:
        ip = d['ip']
        if ip not in creds:
            print(f'!! 无账号信息 {ip}，已跳过')
            continue
        c = creds[ip]
        print(f'\n>>> 开始 {ip}')
        results.append(run_device(ip, c['user'], c['pwd'], cmds))

    write_report(results)
    input('\n全部完成，按回车退出...')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit('用户中断')
    finally:
        input('\n按回车退出...')  # 这里会卡住窗口