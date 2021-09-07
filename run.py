import time
import json
import logging
import argparse
import pyautogui
import cv2 as cv
import numpy as np
from PIL import ImageGrab

def is_imgmatch(grabpath, tmplpath, threshold = 0.01, center=[0,0]):
    grab = cv.imread(grabpath)
    tmpl = cv.imread(tmplpath)
    th, tw  = tmpl.shape[:2]
    md      = cv.TM_SQDIFF_NORMED
    result = cv.matchTemplate(grab, tmpl, md)
    min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)
    if md == cv.TM_SQDIFF_NORMED:
        tl = min_loc
    else:
        tl = max_loc
    tr = [tl[0] + tw, tl[1] + th]
    center[0] = (tl[0] + tr[0]) / 2
    center[1] = (tl[1] + tr[1]) / 2

    # logging.debug(tl)
    # logging.debug(tr)
    # logging.debug(center)

    if min_val > float(threshold):
        return False
    # logging.debug("matched:" + grabpath + tmplpath)
    return True

def do_click(x, y, delay = 0):
    if x <= 0 or y <= 0:
        logging.warning("do_click pos invalid!" + str(x) + "," + str(y))
        return
    pyautogui.moveTo(x, y, duration=delay)
    pyautogui.click()
    # logging.debug("clicked:%d,%d,%d" % (x, y, delay))


def mail_send(conf, index):
    import smtplib
    from email.utils import formataddr 
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    from email.mime.multipart import MIMEMultipart

    mailconf = conf['mail']

    my_sender   = mailconf['sender']       # 发件人邮箱账号
    my_pass     = mailconf['passwd']       # 发件人邮箱密码
    my_user     = mailconf['reciver']      # 收件人邮箱账号，我这边发送给自己

    mail = mailconf['conf'][index]
    try:
        msg = MIMEMultipart()
        # 括号里的对应发件人邮箱昵称、发件人邮箱账号    
        msg['From']     = formataddr([mail['name_from'],my_sender])        
        # 括号里的对应收件人邮箱昵称、收件人邮箱账号
        msg['To']       = formataddr([mail['name_to'],my_user])                      
        # 邮件的主题，也可以说是标题
        msg['Subject']  = mail['title'] 
        # 邮件的内容
        content = MIMEText(mail['content'],'plain','utf-8')
        msg.attach(content)
        # 邮件图片
        with open(mail['picture'],'rb') as fp:
            picture = MIMEImage(fp.read())
            picture['Content-Type'] = 'application/octet-stream'
            picture['Content-Disposition'] = 'attachment;filename="pic.png"'
            msg.attach(picture)
 
        server=smtplib.SMTP_SSL(mailconf['smtp_addr'], mailconf['smtp_port'])  # 发件人邮箱中的SMTP服务器，端口是25
        server.login(my_sender, my_pass)  # 括号中对应的是发件人邮箱账号、邮箱密码
        server.sendmail(my_sender,[my_user,],msg.as_string())  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        server.quit()  # 关闭连接
    except Exception:  # 如果 try 中的语句没有执行，则会执行下面的 ret=False
        logging.warning("mail 邮件发送失败!", exc_info=True)
        return False
    logging.debug("mail 邮件发送成功:" + str(index) + mail['title'])

def fix_pos(conf, pos):
    if not conf['grab']['usebox'] == 'true':
        return
    box = conf['grab']['box'].split(',')
    pos[0] += box[0]
    pos[1] += box[1]

def main():
    # 命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", default="conf.json", dest="config_file")
    args = parser.parse_args()

    # 设置日志格式
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT)

    logging.debug("START!")

    # 读取配置文件
    with open(args.config_file, 'r', encoding='utf-8-sig') as f:
        conf = json.load(f)

    savepath    = conf['grab']['savepath']
    threshold   = conf['match']['threshold']

    while True:
        time.sleep(conf['grab']['interval'])

        # 截图
        box = [0, 0, 0, 0]
        if not conf['grab']['usebox'] == 'true':
            img = ImageGrab.grab()
        else:
            box = conf['grab']['box'].split(',')
            img = ImageGrab.grab(bbox=(int(box[0]), int(box[1]), int(box[2]), int(box[3])))
        img.save(savepath)

        # 匹配
        for tmpl in conf['match']['conf']:
            if tmpl == '__tmplpath__':
                continue
            if not is_imgmatch(savepath, tmpl, threshold):
                continue
            logging.debug("matched:" + tmpl)
            steps = conf['match']['conf'][tmpl]
            for op in steps:
                value = steps[op] 
                if op == "SLEEP":
                    sleep(value)
                elif op == "CLICK_POS":
                    pos = value.split(',')
                    do_click(int(pos[0]), int(pos[1]))  
                    logging.debug("clicked pos:" + str(pos))
                elif op == "CLICK_IMG":
                    pos = [0, 0]
                    if is_imgmatch(savepath, value, threshold, pos):
                        fix_pos(conf, pos)
                        do_click(int(pos[0]), int(pos[1]))  
                        logging.debug("clicked img:" + str(pos))
                    else:
                        logging.warning("click img not match")
                elif op == "MAIL_SEND":
                    mail_send(conf, value)
                else:
                    logging.warning("invalid step op:" + op)


if __name__ == '__main__':
    main()