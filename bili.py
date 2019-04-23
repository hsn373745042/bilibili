import requests
import time
import re
from PIL import Image
from selenium import webdriver
from selenium.webdriver import ActionChains
from urllib.request import urlretrieve
from bs4 import BeautifulSoup

# 一、获取验证码图片
# 初始化函数
def init():
    global url,brower,username,password
    url = 'https://passport.bilibili.com/login'
    # 将自动操作谷歌浏览器实例化
    brower = webdriver.Chrome()
    username = input('请输入你的手机号/邮箱：')
    password = input('请输入你的密码：')
# 模拟登录
def login():
    # 解析url
    brower.get(url)
    # 定位用户名输入框并键入用户名
    user = brower.find_element_by_id('login-username')
    user.send_keys(username)
    time.sleep(2)
    # 定位密码输入框并键入密码
    passwd = brower.find_element_by_id('login-passwd')
    passwd.send_keys(password)
    # 等待两秒模拟人是速度
    time.sleep(2)
# 获取验证码图片
def get_image(img):
    # 模拟鼠标移动到验证码滑块位置，只有鼠标在滑块位置才会加载出验证码图片数据
    w = brower.find_element_by_class_name('gt_slider_knob')
    ActionChains(brower).move_to_element(w).perform()
    # 获取完整渲染的网页源代码，<class 'str'>
    res = brower.page_source
    soup = BeautifulSoup(res,'html.parser')
    imgs = soup.find_all('div',class_='gt_cut_'+img+'_slice')
    # 获取url，正则提取的是字符串
    img_url = re.findall('http.*webp',imgs[0]['style'])[0].replace('webp','jpg')
    # urlretrieve()下载图片
    filename = img+'.jpg'
    urlretrieve(url=img_url,filename=filename)
    image = Image.open(filename)
    # 据观察，下载下来的验证码图片是由无序小图片拼接的，需要自行根据各小图片位置信息重新拼接
    position = get_position(imgs)
    return image,position
# 获取小图片位置信息
def get_position(img):
    img_position = []
    for small_img in img:
        position = {}
        # 小图片x坐标
        position['x'] = int(re.findall('background-position: (.*)px (.*)px;',small_img['style'])[0][0])
        # 小图片y坐标
        position['y'] = int(re.findall('background-position: (.*)px (.*)px;',small_img['style'])[0][1])
        img_position.append(position)
    return img_position
# 裁剪小图片
def Crop(image,position):
    # 第一行图片信息
    first_line_img = []
    # 第二行图片信息
    second_line_img = []
    for pos in position:
        # 小图片一共两行，一行是-58px，一行是0px
        if pos['y'] == -58:
            # 小图片的宽度为10，高度为58，在网页观察所得
            box = (abs(pos['x']), 58, abs(pos['x']) + 10, 116)
            first_line_img.append(image.crop(box))
        if pos['y'] == 0:
            box = (abs(pos['x']), 0, abs(pos['x']) + 10, 58)
            second_line_img.append(image.crop(box))
    return first_line_img,second_line_img
# 将小图片按正确顺序拼接
def put_together(first_line_img,second_line_img,c):
    # 创建新图片，宽度为10（像素）*26（张），高度为116
    big_image = Image.new('RGB', (260, 116))
    # 初始化偏移量
    offset = 0
    # 拼接第一行
    for img in first_line_img:
        big_image.paste(img,(offset, 0))
        offset += img.size[0]
    # 拼接第二行
    x_offset = 0
    for img in second_line_img:
        big_image.paste(img,(x_offset, 58))
        x_offset += img.size[0]
    big_image.save(c)
    return big_image

# 二、获取缺口位置
# 计算缺口位置
def get_distance(bg_image,full_image):
    test = []
    # 遍历像素点横坐标
    for i in range(full_image.size[0]):
        # 遍历像素点纵坐标
        for j in range(full_image.size[1]):
            # 获取缺口图片的像素点
            big_pixel = bg_image.load()[i,j]
            # 获取完整图片的像素点
            big_full_pixel = full_image.load()[i,j]
            # 设定阈值，像素差超过阈值则认为该像素不同
            threshold = 60
            if abs(big_pixel[0] - big_full_pixel[0]) < threshold and abs(big_pixel[1] - big_full_pixel[1]) < threshold and abs(big_pixel[2] - big_full_pixel[2]) < threshold:
                continue
            else:
                test.append(i)
    # test[0]为缺口左上角的横坐标，6是滑块的初始位置，通过观察网页估算
    distance = test[0] - 6
    return distance

# 三、模拟拖动
# 构造滑块轨迹
def get_trace(distance):
    #创建存放轨迹信息列表
    trace = []
    # 加速阶段，在纸上简单计算了下，假设全程用2s，加速1.5s，减速0.5s，
    # 两个加速度的大小相同，那么加速阶段应该为全程的9/10。
    faster_distance = distance * (9/10)
    # 设置初始位置，速度，时间
    start, v0, t = 0, 0, 0.1
    # 把加速度设小点可以减少出现滑块超过正确位置的现象
    while start < distance:
        # 在加速阶段
        if start < faster_distance:
            # 加速度为0.5
            a = 0.5
        else:
            # 加速度为-1
            a = -0.5
        move = v0 * t + (1 / 2) * a * t * t
        v = v0 + a * t
        v0 = v
        start += move
        # 将移动的轨迹放入列表
        trace.append(round(move))
    return trace
# selenium模拟拖动
def move(trace):
    w = brower.find_element_by_class_name('gt_slider_knob')
    # 按住滑块
    ActionChains(brower).click_and_hold(w).perform()
    for i in trace:
        # 滑动滑块
        ActionChains(brower).move_by_offset(xoffset=i, yoffset=0).perform()
    time.sleep(0.5)
    # 释放滑块
    ActionChains(brower).release().perform()
    time.sleep(5)
# 刷新验证码（部分验证码的理论拖动距离与实际稍微有偏差，没有想出解决办法，只能取巧）
def refresh():
    w = brower.find_element_by_class_name('gt_slider_knob')
    ActionChains(brower).move_to_element(w).perform()
    e = brower.find_element_by_class_name('gt_refresh_button')
    ActionChains(brower).move_to_element(e).perform()
    e.click()
    time.sleep(1)
# 主函数
def main():
    init()
    login()
    # 用循环是为了避免遇到1、2张还没破解的图片，并且可以反反爬，有时即使是验证码正确也会被要求重新验证。
    i = 1
    while i == 1:
        bg,bg_position = get_image('bg')
        fullbg,fullbg_position = get_image('fullbg')
        bg_first_line_img,bg_second_line_img = Crop(bg,bg_position)
        fullbg_first_line_img,fullbg_second_line_img = Crop(fullbg,fullbg_position)
        bg_image = put_together(bg_first_line_img,bg_second_line_img,'bg.jpg')
        fullbg_image = put_together(fullbg_first_line_img,fullbg_second_line_img,'fullbg.jpg')
        distance = get_distance(bg_image,fullbg_image)
        trace = get_trace(distance)
        move(trace)
        try:
            refresh()
            i = 1
        except:
            i += 1
            time.sleep(5)
    # 登录成功，5秒后自动关闭浏览器
    time.sleep(5)
    brower.quit()

if __name__ == '__main__':
    main()