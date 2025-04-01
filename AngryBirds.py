import pygame
import math
import sys
import random

# Setup
pygame.init()
WIDTH, HEIGHT = 1200, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Angry Birds – Final Tuned Version")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
RED = (220, 30, 30)
BLACK = (0, 0, 0)
GREEN = (50, 200, 50)
BROWN = (139, 69, 19)
BLUE = (50, 50, 255)
GREY = (120, 120, 120)
YELLOW = (255, 200, 0)

# Constants
gravity = 0.5
ground_y = 510
anchor = (250, 350)
catapult_arm_left = (240, 350)
catapult_arm_right = (260, 350)
font = pygame.font.SysFont(None, 30)

# Game state
score = 0
shots_left = 3
victory = False
bird_stopped_timer = 0

# Load images
background_img = pygame.image.load("background.jpg")
background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT-10))

# Bird sprites
bird_imgs = [
    pygame.transform.scale(pygame.image.load("bird1.png"), (35, 35)),
    pygame.transform.scale(pygame.image.load("bird2.png"), (35, 35)),
    pygame.transform.scale(pygame.image.load("bird3.png"), (35, 35))
]
current_bird_img = bird_imgs[0]
bird_radius = 17

# Block images
block_img = pygame.transform.scale(pygame.image.load("block.png"), (40, 40))
hit_block_img = pygame.transform.scale(pygame.image.load("hit_block.png"), (40, 40))

# Bird setup
bird_start = [247, 335]
bird_pos = list(bird_start)
bird_velocity = [0, 0]
launched = False
dragging = False

# Block class
class Block(pygame.Rect):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 40)
        self.velocity = [0, 0]
        self.initial_pos = (x, y)
        self.hit = False
        self.scored = False
        self.resting_on = None
        self._x = float(x)
        self._y = float(y)
        self.stable_counter = 0

    def update(self, others):
        # Apply gravity
        self.velocity[1] += gravity * 1.2
        
        # Reset resting
        previous_resting = self.resting_on
        self.resting_on = None
        
        # Handle collisions
        for other in others:
            if other is not self and self.colliderect(other):
                # Collision vectors
                self_center_x = self.x + self.width/2
                self_center_y = self.y + self.height/2
                other_center_x = other.x + other.width/2
                other_center_y = other.y + other.height/2
                
                dx = self_center_x - other_center_x
                dy = self_center_y - other_center_y
                
                if abs(dx) > abs(dy):  # Horizontal collision
                    # Friction calculation
                    friction_factor = 0.4
                    
                    rel_vel_x = self.velocity[0] - other.velocity[0]
                    
                    friction_force = rel_vel_x * friction_factor
                    
                    # Transfer momentum
                    self.velocity[0] -= friction_force
                    other.velocity[0] += friction_force * 0.8
                    
                    # Prevent overlap
                    if dx > 0:
                        self._x = other.right + 1.0
                    else:
                        self._x = other.left - self.width - 1.0
                    
                else:  # Vertical collision
                    if dy < 0:  # Above other
                        self._y = other.top - self.height
                        
                        # Prevent bounce jitter
                        bounce_factor = -0.01
                        
                        if abs(self.velocity[1]) < 0.3:
                            self.velocity[1] = 0
                        else:
                            self.velocity[1] *= bounce_factor
                        
                        # Set resting
                        self.resting_on = other
                        
                        # Stack friction
                        stack_friction = 0.01
                        
                        rel_vel_x = self.velocity[0] - other.velocity[0]
                        
                        if abs(rel_vel_x) > 0.1:
                            friction_force = rel_vel_x * stack_friction
                            self.velocity[0] -= friction_force
                            other.velocity[0] += friction_force * 0.7
                    
                    elif dy > 0:  # Below other
                        self.y = other.bottom
                        self.velocity[1] = max(0, self.velocity[1])
                        
                        # Horizontal friction
                        stack_friction = 0.7
                        rel_vel_x = self.velocity[0] - other.velocity[0]
                        if abs(rel_vel_x) > 0.1:
                            friction_force = rel_vel_x * stack_friction
                            self.velocity[0] -= friction_force
                            other.velocity[0] += friction_force * 0.7
        
        # Update positions
        self._x = getattr(self, '_x', float(self.x))
        self._y = getattr(self, '_y', float(self.y))
        
        self._x += self.velocity[0]
        self._y += self.velocity[1]
        
        # Integer conversion
        self.x = int(self._x)
        self.y = int(self._y)
        
        # Ground collision
        if self._y + self.height > ground_y:
            self._y = ground_y - self.height
            
            if self.velocity[1] > 0.3:
                self.velocity[1] *= -0.2
            else:
                self.velocity[1] = 0
                
            # Ground friction
            if abs(self.velocity[0]) < 0.5:
                self.velocity[0] *= 0.7
            else:
                self.velocity[0] *= 0.9
        
        # Apply damping
        self.velocity[0] *= 0.99
        
        # Remove micro-movements
        if abs(self.velocity[0]) < 0.05:
            self.velocity[0] = 0
        
        if abs(self.velocity[1]) < 0.05:
            self.velocity[1] = 0
            
        # Stabilize block
        if abs(self.velocity[0]) < 0.1 and abs(self.velocity[1]) < 0.1:
            self.stable_counter += 1
            if self.stable_counter > 15:
                self.velocity = [0, 0]
        else:
            self.stable_counter = 0
        
        # Check movement
        dx = abs(self.x - self.initial_pos[0])
        dy = abs(self.y - self.initial_pos[1])
        if (dx > 5 or dy > 5) and not self.scored:
            self.hit = True
            self.scored = True
            global score
            score += 10

    def draw(self, surf):
        # Draw block
        if self.hit:
            surf.blit(hit_block_img, (self.x, self.y))
        else:
            surf.blit(block_img, (self.x, self.y))

# Generate level
def generate_random_level():
    structures = []
    
    num_towers = random.randint(2, 4)
    
    for t in range(num_towers):
        tower_x = 750 + t * 100
        tower_height = random.randint(2, 5)
   
        for h in range(tower_height):
            block = Block(tower_x, ground_y - 40 - h*40)
            structures.append(block)
            
        if random.random() < 0.4 and t < num_towers - 1:
            next_tower_x = 550 + (t+1) * 100
            bridge_height = random.randint(1, min(tower_height, 3))
            bridge_y = ground_y - 40 - (bridge_height-1)*40

            mid_x = (tower_x + next_tower_x) // 2 - 20
            horizontal_block = Block(mid_x, bridge_y)
            structures.append(horizontal_block)
    
    return structures

blocks = generate_random_level()

# Reset bird
def reset_bird():
    global bird_pos, bird_velocity, launched, dragging, current_bird_img, bird_stopped_timer
    bird_pos = list(bird_start)
    bird_velocity = [0, 0]
    launched = False
    dragging = False
    bird_stopped_timer = 0
    current_bird_img = random.choice(bird_imgs)

# Reset game
def full_reset():
    global score, shots_left, victory, blocks, current_bird_img, bird_pos, bird_velocity, launched, dragging, bird_stopped_timer
    score = 0
    shots_left = 3
    victory = False
    bird_pos = list(bird_start)
    bird_velocity = [0, 0]
    launched = False
    dragging = False
    bird_stopped_timer = 0

    current_bird_img = bird_imgs[0]
    blocks = generate_random_level()

# Game loop
running = True
while running:
    # Draw background
    if background_img:
        screen.blit(background_img, (0, 0))
    else:
        screen.fill(WHITE)

    # Input handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if not launched and not victory and shots_left > 0:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if math.hypot(mx - bird_pos[0], my - bird_pos[1]) < bird_radius + 10:
                    dragging = True

            if dragging and event.type == pygame.MOUSEMOTION:
                mx, my = pygame.mouse.get_pos()
                bird_pos = [mx, my]

            if dragging and event.type == pygame.MOUSEBUTTONUP:
                dx = anchor[0] - bird_pos[0]
                dy = anchor[1] - bird_pos[1]
                bird_velocity = [dx * 0.3, dy * 0.3]
                launched = True
                dragging = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                full_reset()

    # Bird physics
    if launched and shots_left > 0:
        bird_velocity[1] += gravity * 1.3
        bird_pos[0] += bird_velocity[0]
        bird_pos[1] += bird_velocity[1]

        # Bird-block collisions
        bird_rect = pygame.Rect(bird_pos[0]-bird_radius, bird_pos[1]-bird_radius, bird_radius*2, bird_radius*2)
        collision_occurred = False
        
        for block in blocks:
            if bird_rect.colliderect(block):
                collision_occurred = True
                
                # Transfer momentum
                block.velocity[0] += bird_velocity[0] * 0.25
                block.velocity[1] += bird_velocity[1] * 0.25
                
                # Calculate normal
                center_bird_x = bird_pos[0]
                center_bird_y = bird_pos[1]
                center_block_x = block.x + block.width/2
                center_block_y = block.y + block.height/2
                
                dx = center_bird_x - center_block_x
                dy = center_bird_y - center_block_y
                
                # Normalize vector
                length = max(0.1, math.sqrt(dx*dx + dy*dy))
                dx /= length
                dy /= length
                
                # Reflect velocity
                dot = bird_velocity[0]*dx + bird_velocity[1]*dy
                bird_velocity[0] = (-2 * dot * dx + bird_velocity[0]) * 0.65
                bird_velocity[1] = (-2 * dot * dy + bird_velocity[1]) * 0.65
                
                # Prevent overlap
                overlap = bird_radius - length
                if overlap > 0:
                    bird_pos[0] += dx * overlap * 1.1
                    bird_pos[1] += dy * overlap * 1.1
                
                break
        
        # Ground collision
        if bird_pos[1] + bird_radius > ground_y:
            bird_pos[1] = ground_y - bird_radius
            bird_velocity[1] *= -0.4
            bird_velocity[0] *= 0.85
        
        # Check stopped
        bird_speed = math.sqrt(bird_velocity[0]**2 + bird_velocity[1]**2)
        
        if bird_speed < 0.5:
            bird_stopped_timer += 1
            if bird_stopped_timer > 60:
                shots_left = max(shots_left - 1, 0)
                if shots_left > 0:
                    reset_bird()
                launched = False
        else:
            bird_stopped_timer = 0

        if bird_pos[1] > HEIGHT or bird_pos[0] > WIDTH or bird_pos[0] < -50:
            bird_stopped_timer = 121

    # Update blocks
    all_hit = True
    for block in blocks:
        block.update(blocks)
        block.draw(screen)
        if not block.hit:
            all_hit = False

    if all_hit and not victory:
        victory = True

    # Draw slingshot
    pygame.draw.line(screen, BLACK, (0, ground_y), (WIDTH, ground_y), 1)
    pygame.draw.line(screen, BROWN, (anchor[0]-20, anchor[1]+30), catapult_arm_left, 8)
    pygame.draw.line(screen, BROWN, (anchor[0]+20, anchor[1]+30), catapult_arm_right, 8)
    if not launched and not victory and shots_left > 0:
        pygame.draw.line(screen, GREY, catapult_arm_left, bird_pos, 2)
        pygame.draw.line(screen, GREY, catapult_arm_right, bird_pos, 2)

    # Draw bird
    if not victory or launched:
        screen.blit(current_bird_img, (int(bird_pos[0]) - 17, int(bird_pos[1]) - 17))

    # Draw HUD
    score_text = font.render(f"Score: {score}", True, BLACK)
    shots_text = font.render(f"Shots Left: {shots_left}", True, BLACK)
    restart_text = font.render("Press R to Restart", True, BLACK)
    
    pygame.draw.rect(screen, (255, 255, 255, 180), (5, 5, score_text.get_width() + 10, score_text.get_height() + 10))
    pygame.draw.rect(screen, (255, 255, 255, 180), (5, 35, shots_text.get_width() + 10, shots_text.get_height() + 10))
    pygame.draw.rect(screen, (255, 255, 255, 180), (5, 65, restart_text.get_width() + 10, restart_text.get_height() + 10))
    
    screen.blit(score_text, (10, 10))
    screen.blit(shots_text, (10, 40))
    screen.blit(restart_text, (10, 70))

    # Game state messages
    if victory:
        victory_text = font.render("Victory! All blocks moved!", True, YELLOW)
        pygame.draw.rect(screen, (0, 0, 0, 180), (WIDTH//2 - 170, 15, victory_text.get_width() + 20, victory_text.get_height() + 10))
        screen.blit(victory_text, (WIDTH//2 - 160, 20))
    elif shots_left == 0 and not victory:
        game_over_text = font.render("Out of shots! Press R to try again.", True, RED)
        pygame.draw.rect(screen, (0, 0, 0, 180), (WIDTH//2 - 180, 15, game_over_text.get_width() + 20, game_over_text.get_height() + 10))
        screen.blit(game_over_text, (WIDTH//2 - 170, 20))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()