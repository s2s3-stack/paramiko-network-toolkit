import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path

MAIL_CONFIGS = {
    'qq': {'smtp': 'smtp.qq.com', 'port': 465},
    '163': {'smtp': 'smtp.163.com', 'port': 465},
    '126': {'smtp': 'smtp.126.com', 'port': 465},
    'sina': {'smtp': 'smtp.sina.com', 'port': 465},
    'aliyun': {'smtp': 'smtp.aliyun.com', 'port': 465}
}

def send_email(email_type, sender, password, receivers, subject, content, attachments=None):
    if email_type.lower() not in MAIL_CONFIGS:
        raise ValueError(f"不支持的邮箱类型: {email_type}")
    config = MAIL_CONFIGS[email_type.lower()]
    smtp_server = config['smtp']
    smtp_port = config['port']
    
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ', '.join(receivers) if isinstance(receivers, list) else receivers
    msg['Subject'] = subject
    msg.attach(MIMEText(content, 'plain', 'utf-8'))
    
    if attachments:
        for attachment in attachments:
            if Path(attachment).exists():
                with open(attachment, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=Path(attachment).name)
                part['Content-Disposition'] = f'attachment; filename="{Path(attachment).name}"'
                msg.attach(part)
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender, password)
        if isinstance(receivers, str):
            receivers = [r.strip() for r in receivers.split(',')]
        server.sendmail(sender, receivers, msg.as_string())
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError:
        return False
    except Exception:
        return False

def ask_email_config(current_config):
    print("\n" + "="*60)
    print("邮件发送配置")
    print("="*60)
    print(f"当前发件人: {current_config['sender']}")
    print(f"当前收件人: {', '.join(current_config['receivers'])}")
    
    try:
        change = input("\n是否修改邮件配置？(y/n, 回车使用当前配置): ").strip().lower()
    except KeyboardInterrupt:
        return current_config
    if change != 'y':
        return current_config
    
    email_type = input(f"邮箱类型 (qq/163, 默认:{current_config['type']}): ").strip().lower()
    if not email_type:
        email_type = current_config['type']
    
    sender = input(f"发件人邮箱 (默认:{current_config['sender']}): ").strip()
    if not sender:
        sender = current_config['sender']
    
    password = input("邮箱授权码 (留空则使用保存的授权码): ").strip()
    if not password:
        password = current_config['password']
    
    receivers_input = input(f"收件人邮箱 (多个用逗号分隔, 默认使用当前配置): ").strip()
    if receivers_input:
        receivers = [r.strip() for r in receivers_input.split(',')]
    else:
        receivers = current_config['receivers']
    
    return {
        'type': email_type,
        'sender': sender,
        'password': password,
        'receivers': receivers
    }