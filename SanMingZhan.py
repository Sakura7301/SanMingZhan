import os  
import io  
import pytz  
import plugins  
from config import conf  
from datetime import datetime  
from bridge.context import ContextType  
from bridge.reply import Reply, ReplyType  
from common.log import logger  
from plugins import *  
from PIL import Image, ImageDraw, ImageFont  


@plugins.register(  
    name="SanMingZhan",  # 插件名称  
    desire_priority=99,  # 插件优先级  
    hidden=False,  # 是否隐藏  
    desc="三命占排盘",  # 插件描述  
    version="1.0",  # 插件版本  
    author="sakura7301",  # 作者  
)  
class SanMingZhan(Plugin):  
    def __init__(self):  
        super().__init__()  # 调用父类的初始化  
        self.cards = list(range(1, 50))  
        self.OUTPUT_DIR = "./plugins/SanMingZhan/image"   
        # 删除排盘历史记录  
        self.delete_all_files_in_directory(self.OUTPUT_DIR)  
        # 注册处理上下文的事件  
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context  
        logger.info("[SanMingZhan] 插件初始化完毕")  

    def delete_all_files_in_directory(self, directory):  
        """删除指定目录下的所有文件"""  
        if not os.path.exists(directory):  
            logger.warning(f"目录不存在: {directory}")  
            return "目录不存在"  # 返回特定消息  

        try:  
            # 遍历目录中的所有文件和子目录  
            for filename in os.listdir(directory):  
                file_path = os.path.join(directory, filename)  
                # 检查是否是文件  
                if os.path.isfile(file_path):  
                    os.remove(file_path)  # 删除文件  
                    logger.info(f"已清除文件: {file_path}")  
        except Exception as e:  
            logger.error(f"发生错误: {e}")   

    def ensure_directory_exists(self, directory):  
        """检查指定目录是否存在，如果不存在则创建该目录"""  
        try:  
            if not os.path.exists(directory):  
                os.makedirs(directory)  # 创建目录  
                logger.info(f"目录已创建: {directory}")  
            else:  
                logger.debug(f"目录已存在: {directory}")  
        except Exception as e:  
            logger.error(f"发生错误: {e}")  

    def SanMingZhanRequest(self, query):  
        # 定义占卜关键词列表  
        divination_keywords = ['三命占', "三命九宫"]  
        return any(keyword in query for keyword in divination_keywords)  

    def get_current_filename(self):  
        """  
        生成当前时间的文件名  
        格式：./pai_pan_年_月_日_时.png  
        """  
        beijing_tz = pytz.timezone('Asia/Shanghai')  
        current_time = datetime.now(beijing_tz)  
        # 检查目录  
        self.ensure_directory_exists(self.OUTPUT_DIR)  
        return f"{self.OUTPUT_DIR}/pai_pan_{current_time.year}_{current_time.month}_{current_time.day}_{current_time.hour}.png"  

    def get_rotation_start_position(self, hour):  
        """  
        根据小时数确定起始位置  
        返回起始位置的索引（基于八卦位置）  
        """  
        hour_to_position = {  
            12: 7,  # 劫伤  
            1: 7,   # 劫伤  
            2: 6,   # 天帙  
            3: 3,   # 小安  
            4: 3,   # 小安  
            5: 0,   # 空亡  
            6: 1,   # 速喜  
            7: 1,   # 速喜  
            8: 2,   # 地捷  
            9: 5,   # 赤口  
            10: 5,  # 赤口  
            11: 8   # 禄存  
        }  
        return hour_to_position.get(hour, 0)  

    def arrange_terms_by_hour(self, terms, hour):  
        """  
        根据给定的小时数重新排列词语，逆时针排列  
        """  
        if len(terms) != 8:  
            raise ValueError("必须提供8个词语")  
        
        positions = [0, 1, 2, 5, 8, 7, 6, 3]  
        start_pos = self.get_rotation_start_position(hour)  
        
        result = [''] * 9  
        result[4] = '天魁星'  

        start_idx = positions.index(start_pos)  
        
        for i in range(8):  
            pos_idx = (start_idx + i) % 8  
            actual_pos = positions[pos_idx]  
            result[actual_pos] = terms[i]  
        
        return result  

    def create_gradient_background(self, width, height):  
        """  
        创建渐变背景  
        """  
        background = Image.new('RGB', (width, height))  
        for y in range(height):  
            r = int(250 - (y / height) * 10)  
            g = int(245 - (y / height) * 10)  
            b = int(235 - (y / height) * 10)  
            for x in range(width):  
                background.putpixel((x, y), (r, g, b))  
        return background  

    def get_text_dimensions(self, text, font):  
        """  
        获取文本尺寸  
        """  
        if hasattr(font, 'getsize'):  
            return font.getsize(text)  
        else:  
            # 对于较新版本的Pillow  
            bbox = font.getbbox(text)  
            return bbox[2] - bbox[0], bbox[3] - bbox[1]  

    def draw_centered_text(self, draw, text, x, y, width, height, font, color):  
        """  
        在指定区域内居中绘制文本  
        """  
        if font is None:  
            logger.error("无法绘制文本，因为字体对象是 None")  
            return  
        
        text_width, text_height = self.get_text_dimensions(text, font)  
        text_x = x + (width - text_width) // 2  
        text_y = y + (height - text_height) // 2  
        draw.text((text_x, text_y), text, font=font, fill=color)  

    def create_image_from_grid(self, grid, current_time, shichen_name, output_path):  
        """  
        将九宫格转换为图片，带有优化的视觉效果  
        """  
        # 设置图片尺寸和颜色  
        width = 800  
        height = 900  
        main_color = (45, 45, 48)  
        secondary_color = (75, 75, 78)  
        grid_color = (100, 100, 103)  
        center_color = (30, 30, 33)  

        # 创建渐变背景  
        image = self.create_gradient_background(width, height)  
        draw = ImageDraw.Draw(image)  

        # 加载字体  
        try:  
            font_paths = [  
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  
                "C:\\Windows\\Fonts\\simhei.ttf",  
                "/System/Library/Fonts/PingFang.ttc",  
                "/System/Library/Fonts/STHeiti Light.ttc"  
            ]  

            title_font = None  
            main_font = None  
            sub_font = None  
            center_font = None  

            for path in font_paths:  
                if os.path.exists(path):  
                    title_font = ImageFont.truetype(path, 48)  
                    main_font = ImageFont.truetype(path, 32)  
                    sub_font = ImageFont.truetype(path, 24)  
                    center_font = ImageFont.truetype(path, 36)  
                    break  

            # 设置默认字体以防字体加载失败  
            if title_font is None:  
                title_font = ImageFont.load_default()  
            if main_font is None:  
                main_font = ImageFont.load_default()  
            if sub_font is None:  
                sub_font = ImageFont.load_default()  
            if center_font is None:  
                center_font = ImageFont.load_default()  

        except Exception as e:  
            logger.error(f"加载字体时出错: {e}")  
            title_font = main_font = sub_font = center_font = ImageFont.load_default()    

        # 绘制外框  
        margin = 30  
        draw.rectangle([margin, margin, width - margin, height - margin], outline=main_color, width=2)  

        # 绘制标题和时间信息  
        title = "三命九宫"  
        title_width, _ = self.get_text_dimensions(title, title_font)  
        title_x = (width - title_width) // 2  

        try:  
            draw.text((title_x, 50), title, font=title_font, fill=main_color)  
            draw.text((60, 120), f"当前时间：{current_time}", font=sub_font, fill=secondary_color)  
            draw.text((60, 160), f"当前时辰：{shichen_name}", font=sub_font, fill=secondary_color)  
        except Exception as e:  
            logger.error(f"绘制标题时出错: {e}")  

        # 绘制九宫格  
        start_y = 220  
        cell_width = (width - 120) // 3  
        cell_height = 180  

        # 绘制网格底色和线条  
        for row in range(3):  
            for col in range(3):  
                x1 = 60 + col * cell_width  
                y1 = start_y + row * cell_height  
                x2 = x1 + cell_width  
                y2 = y1 + cell_height  
                
                # 绘制单元格背景  
                if row * 3 + col == 4:  # 中心格子  
                    draw.rectangle([x1, y1, x2, y2], fill=(240, 235, 225))  
                else:  
                    draw.rectangle([x1, y1, x2, y2], fill=(245, 240, 230))  

        # 绘制网格线  
        for i in range(4):  
            y = start_y + i * cell_height  
            draw.line([(60, y), (width - 60, y)], fill=grid_color, width=2)  
        for i in range(4):  
            x = 60 + i * cell_width  
            draw.line([(x, start_y), (x, start_y + 3 * cell_height)], fill=grid_color, width=2)  

        # 填充内容  
        for row in range(3):  
            for col in range(3):  
                idx = row * 3 + col  
                cell = grid[idx]  
                x1 = 60 + col * cell_width  
                y1 = start_y + row * cell_height  

                is_center = (row == 1 and col == 1)  
                current_font = center_font if is_center else main_font  
                current_color = center_color if is_center else main_color  

                # 计算每个文本项的高度  
                total_items = len([item for item in cell if item])  
                item_height = cell_height / (total_items + 1)  
                
                # 绘制每个文本项  
                for i, text in enumerate([item for item in cell if item]):  
                    if text:  
                        try:  
                            if is_center:  
                                # 中宫文字加粗效果  
                                y_pos = y1 + (i + 1) * item_height  
                                self.draw_centered_text(draw, text,  
                                                    x1,  
                                                    y_pos - 20,  
                                                    cell_width,  
                                                    40,  
                                                    center_font,  
                                                    current_color)  
                            else:  
                                text_color = main_color if i == 0 else secondary_color  
                                y_pos = y1 + (i + 1) * item_height  
                                self.draw_centered_text(draw, text,  
                                                    x1,  
                                                    y_pos - 20,  
                                                    cell_width,  
                                                    40,  
                                                    main_font,  
                                                    text_color)  
                        except Exception as e:  
                            logger.error(f"绘制文字时出错: {e}")  

        # 保存图片  
        try:  
            image.save(output_path, quality=95)  
        except Exception as e:  
            logger.error(f"保存图片时出错: {e}")  
            image = image.convert('RGB')  
            image.save(output_path, quality=95)  
        
        return image  

    def SanMingJiuGong(self):  
        """  
        创建九宫格显示并返回图片内容  
        """  
        # 获取当前文件名  
        current_filename = self.get_current_filename()  
        
        # 检查文件是否已存在  
        if os.path.exists(current_filename):  
            logger.info(f"找到已存在的图片：{current_filename}")  
            try:  
                with open(current_filename, 'rb') as f:  
                    image_content = f.read()  
                return io.BytesIO(image_content)  
            except Exception as e:  
                logger.error(f"读取已存在图片失败：{e}")  
                # 如果读取失败，继续执行生成新图片的流程  
        
        # 基础数据  
        bagua = ['巽', '离', '坤', '震', '', '兑', '艮', '坎', '乾']  
        dizhi = ['辰', '巳午', '未', '寅卯', '', '申酉', '丑', '子亥', '戌']  
        terms = ['空亡', '速喜', '地捷', '小安', '命宫', '赤口', '天帙', '劫伤', '禄存']  
        fei_xing = ["天罡星", "天机星", "天贵星", "天孤星", "天暗星", "天速星", "天剑星", "天损星"]  
        
        # 获取当前时辰  
        hour = self.get_current_shichen()  
        logger.info(f"hour: {hour}")  
        shichen_name = self.get_shichen_name(hour)  
        
        # 获取当前北京时间  
        beijing_time = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S') 

        # 处理额外词组  
        if fei_xing is not None:  
            if len(fei_xing) != 8:  
                raise ValueError("额外词组必须包含8个词组")  
            if hour is not None and 1 <= hour <= 12:  
                full_additional = self.arrange_terms_by_hour(fei_xing, hour)  
            else:  
                full_additional = fei_xing[:4] + ['天魁星'] + fei_xing[4:]  
        
        # 创建网格数据  
        grid = []  
        for i in range(9):  
            cell = [bagua[i], dizhi[i], terms[i]]  
            if fei_xing is not None:  
                cell.append(full_additional[i])  
            grid.append(cell)  

        logger.info(f"创建的网格内容为: {grid}") 
        
        # 创建并保存图片  
        self.create_image_from_grid(grid, beijing_time, shichen_name, current_filename)  
        
        # 读取并返回新生成的图片  
        try:  
            with open(current_filename, 'rb') as f:  
                image_content = f.read()  
            logger.info(f"成功生成并读取新图片：{current_filename}")  
            return io.BytesIO(image_content)  
        except Exception as e:  
            logger.error(f"读取新生成的图片失败：{e}")  
            return None  

    def get_current_shichen(self):  
        """  
        获取当前时辰对应的小时数（1-12）  
        """  
        beijing_tz = pytz.timezone('Asia/Shanghai')  
        current_time = datetime.now(beijing_tz)  
        hour = current_time.hour  
        
        if 23 <= hour or hour < 1:  
            return 1  
        elif 1 <= hour < 3:  
            return 2  
        elif 3 <= hour < 5:  
            return 3  
        elif 5 <= hour < 7:  
            return 4  
        elif 7 <= hour < 9:  
            return 5  
        elif 9 <= hour < 11:  
            return 6  
        elif 11 <= hour < 13:  
            return 7  
        elif 13 <= hour < 15:  
            return 8  
        elif 15 <= hour < 17:  
            return 9  
        elif 17 <= hour < 19:  
            return 10  
        elif 19 <= hour < 21:  
            return 11  
        else:  # 21 <= hour < 23  
            return 12  

    def get_shichen_name(self, hour_num):  
        """  
        根据小时数返回时辰名称  
        """  
        shichen_names = {  
            1: "子时 (23:00-1:00)",  
            2: "丑时 (1:00-3:00)",  
            3: "寅时 (3:00-5:00)",  
            4: "卯时 (5:00-7:00)",  
            5: "辰时 (7:00-9:00)",  
            6: "巳时 (9:00-11:00)",  
            7: "午时 (11:00-13:00)",  
            8: "未时 (13:00-15:00)",  
            9: "申时 (15:00-17:00)",  
            10: "酉时 (17:00-19:00)",  
            11: "戌时 (19:00-21:00)",  
            12: "亥时 (21:00-23:00)"  
        }  
        return shichen_names.get(hour_num, "未知时辰")  

    def SanMingZhanRquest(self, query):
        # 定义占卜关键词列表
        divination_keywords = ['三命占', "三命九宫"]
        return any(keyword in query for keyword in divination_keywords)

    
    def on_handle_context(self, e_context: EventContext):  
        """处理上下文事件"""  
        if e_context["context"].type not in [ContextType.TEXT]:  
            logger.debug("[SanMingZhan] 上下文类型不是文本，无需处理")  
            return  
        
        content = e_context["context"].content.strip()  
        logger.debug(f"[SanMingZhan] 处理上下文内容: {content}")  

        if self.SanMingZhanRquest(content):  
            logger.info("[SanMingZhan] 排盘")  
            reply = Reply()  
            image = self.SanMingJiuGong()  # 获取排盘结果  
            reply.type = ReplyType.IMAGE if image else ReplyType.TEXT  
            reply.content = image if image else "排盘失败啦，待会再试试吧~🐾"  
            e_context['reply'] = reply  
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑   


    def get_help_text(self, **kwargs):  
        """获取帮助文本"""  
        help_text = "输入'三命占'或'三命九宫'可得获取电子排盘~🐾\n"  
        return help_text
