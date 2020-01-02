from PIL import Image, ImageGrab
import pytesseract
import time

'''
	读取图片
'''
def _get_file_content(filePath):
	with open(filePath, 'rb') as fp:
		return fp.read()

def get_yzm_text(control):
	point = control.element_info.rectangle
	pic = ImageGrab.grab(bbox=(point.left, point.top, point.right, point.bottom))
	pic.save('./yzm.png')

	## ocr识别验证码
	image = Image.open('./yzm.png')
	result = pytesseract.image_to_string(image)   # 解析图片
	return result