from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoTimeoutException
import time

rsa_path = r'C:\Users\sys400070\.ssh\id_rsa'

device = {
    'device_type': 'hp_comware',
    'host': '192.168.56.102',
    'username': 'admin',
    # 密码可以留着做 fallback（H3C 很多版本支持密钥+密码双认证）
    'password': 'Admin@h3c.com',
    
    # 以下几个参数是关键！！
    'global_delay_factor': 2.0,           # 整体命令等待时间翻倍
    'conn_timeout': 25,                   # 连接超时拉长到 25 秒（默认 10 秒太短）
    'session_log': f'session_{time.strftime("%Y%m%d_%H%M%S")}.log',  # 强烈建议打开日志
    'session_log_record_writes': True,
    'session_log_file_mode': 'write',
    
    # 下面这行在 Windows 上经常救命
    'ssh_config_file': False,             # 先禁用 ssh_config_file 试试
    
    # 直接用 key_file（很多 2024 后版本反而更好用）
    'key_file': rsa_path,
    'use_keys': True,
    'allow_agent': False,                 # 关闭 ssh-agent 干扰
    'look_for_keys': False,
}

print(f"尝试连接 {device['host']} ...")

try:
    with ConnectHandler(**device) as conn:
        print("连接成功！")
        print(conn.send_command("display version").strip())
        
except NetmikoTimeoutException as e:
    print("连接超时...")
    print("建议尝试：")
    print("1. 把 conn_timeout 改成 40")
    print("2. global_delay_factor 改成 3.0 或 4.0")
    print("3. 检查 Windows OpenSSH 是否正常")
    print("4. 看看 session_log 日志最后几行写了什么")
except Exception as e:
    print("其他错误：", str(e))