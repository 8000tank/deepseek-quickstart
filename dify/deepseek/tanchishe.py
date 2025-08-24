import pygame
import random
import time

# 初始化pygame
pygame.init()

# 定义颜色常量
WHITE = (255, 255, 255)      # 白色，用于文字显示
BLACK = (0, 0, 0)            # 黑色，背景色
RED = (255, 0, 0)            # 红色，食物颜色
GREEN = (0, 255, 0)          # 绿色，蛇身颜色
DARK_GREEN = (0, 200, 0)     # 深绿色，蛇头颜色

# 游戏设置参数
WINDOW_WIDTH = 600           # 窗口宽度
WINDOW_HEIGHT = 600          # 窗口高度
BLOCK_SIZE = 20              # 每个网格方块的大小
GAME_AREA_SIZE = 20          # 游戏区域为20x20网格
FPS = 10                     # 游戏帧率

# 创建游戏窗口
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('贪吃蛇游戏')  # 设置窗口标题
clock = pygame.time.Clock()              # 创建时钟对象控制游戏帧率

# 设置字体
font = pygame.font.SysFont('arial', 25)  # 使用Arial字体，大小25


class Snake:
    """蛇类，负责蛇的移动、生长和方向控制"""

    def __init__(self):
        # 初始化蛇的位置，从屏幕中央开始
        self.positions = [(GAME_AREA_SIZE // 2, GAME_AREA_SIZE // 2)]
        self.direction = (1, 0)  # 初始方向向右 (x, y)
        self.grow = False        # 标记蛇是否需要生长

    def get_head_position(self):
        """获取蛇头位置"""
        return self.positions[0]

    def move(self):
        """
        移动蛇
        返回True表示游戏结束（撞到自己），False表示继续游戏
        """
        head_x, head_y = self.get_head_position()
        dir_x, dir_y = self.direction
        # 计算新的头部位置，使用模运算实现穿墙效果
        new_x = (head_x + dir_x) % GAME_AREA_SIZE
        new_y = (head_y + dir_y) % GAME_AREA_SIZE

        # 检查是否撞到自己（新位置是否在蛇身体的其他部分）
        if (new_x, new_y) in self.positions[1:]:
            return True  # 游戏结束

        # 将新的头部位置插入到列表开头
        self.positions.insert(0, (new_x, new_y))
        # 如果不需要生长，则移除尾部
        if not self.grow:
            self.positions.pop()
        else:
            self.grow = False  # 重置生长标记
        return False

    def change_direction(self, new_direction):
        """
        改变蛇的移动方向
        防止直接反向移动（例如向右时不能直接向左）
        """
        # 检查新方向是否与当前方向相反
        if (new_direction[0] * -1, new_direction[1] * -1) != self.direction:
            self.direction = new_direction

    def grow_snake(self):
        """标记蛇需要生长（吃到食物时调用）"""
        self.grow = True


class Food:
    """食物类，负责食物的生成和位置管理"""

    def __init__(self, snake_positions):
        # 初始化食物位置，确保不在蛇身上
        self.position = self.generate_position(snake_positions)

    def generate_position(self, snake_positions):
        """生成不在蛇身上的随机位置"""
        while True:
            position = (random.randint(0, GAME_AREA_SIZE - 1),
                        random.randint(0, GAME_AREA_SIZE - 1))
            if position not in snake_positions:
                return position


def draw_grid():
    """绘制游戏网格线"""
    for x in range(0, WINDOW_WIDTH, BLOCK_SIZE):
        pygame.draw.line(screen, (40, 40, 40), (x, 0), (x, WINDOW_HEIGHT))
    for y in range(0, WINDOW_HEIGHT, BLOCK_SIZE):
        pygame.draw.line(screen, (40, 40, 40), (0, y), (WINDOW_WIDTH, y))


def main():
    """游戏主函数"""
    snake = Snake()  # 创建蛇对象
    food = Food(snake.positions)  # 创建食物对象
    score = 0        # 初始化分数
    game_over = False  # 游戏结束标志
    paused = False     # 游戏暂停标志

    # 游戏主循环
    while True:
        # 处理事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # 点击关闭按钮
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:  # 键盘按下事件
                if event.key == pygame.K_ESCAPE:  # ESC键退出
                    pygame.quit()
                    return
                elif event.key == pygame.K_p:  # P键暂停/继续
                    paused = not paused
                elif not paused and not game_over:  # 游戏进行中且未暂停
                    # 方向键控制
                    if event.key == pygame.K_UP:
                        snake.change_direction((0, -1))  # 上
                    elif event.key == pygame.K_DOWN:
                        snake.change_direction((0, 1))   # 下
                    elif event.key == pygame.K_LEFT:
                        snake.change_direction((-1, 0))  # 左
                    elif event.key == pygame.K_RIGHT:
                        snake.change_direction((1, 0))   # 右
                elif game_over and event.key == pygame.K_RETURN:  # 游戏结束时按回车重新开始
                    # 重置游戏状态
                    snake = Snake()
                    food = Food(snake.positions)
                    score = 0
                    game_over = False

        # 游戏进行中且未暂停
        if not paused and not game_over:
            # 移动蛇并检查是否游戏结束
            game_over = snake.move()

            # 检查是否吃到食物
            if snake.get_head_position() == food.position:
                snake.grow_snake()  # 蛇生长
                food = Food(snake.positions)  # 生成新食物
                score += 10  # 增加分数

            # 绘制游戏画面
            screen.fill(BLACK)  # 清空屏幕为黑色
            draw_grid()  # 绘制网格

            # 绘制食物
            food_rect = pygame.Rect(food.position[0] * BLOCK_SIZE,
                                    food.position[1] * BLOCK_SIZE,
                                    BLOCK_SIZE, BLOCK_SIZE)
            pygame.draw.rect(screen, RED, food_rect)

            # 绘制蛇
            for i, position in enumerate(snake.positions):
                snake_rect = pygame.Rect(position[0] * BLOCK_SIZE,
                                         position[1] * BLOCK_SIZE,
                                         BLOCK_SIZE, BLOCK_SIZE)
                if i == 0:  # 蛇头
                    pygame.draw.rect(screen, DARK_GREEN, snake_rect)
                else:  # 蛇身
                    pygame.draw.rect(screen, GREEN, snake_rect)

            # 显示当前分数
            score_text = font.render(f'分数: {score}', True, WHITE)
            screen.blit(score_text, (10, 10))

        # 游戏结束状态
        elif game_over:
            # 显示游戏结束信息
            game_over_text = font.render('游戏结束! 按Enter重新开始', True, WHITE)
            final_score_text = font.render(f'最终分数: {score}', True, WHITE)
            screen.blit(game_over_text, (WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2 - 30))
            screen.blit(final_score_text, (WINDOW_WIDTH // 2 - 80, WINDOW_HEIGHT // 2 + 10))

        # 游戏暂停状态
        elif paused:
            # 显示暂停信息
            pause_text = font.render('游戏暂停 - 按P继续', True, WHITE)
            screen.blit(pause_text, (WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2))

        # 更新屏幕显示
        pygame.display.update()
        # 控制游戏帧率
        clock.tick(FPS)


# 程序入口点
if __name__ == "__main__":
    main()
