import pygame
import random
import json
import os
import math

pygame.init()

# ---------------- WINDOW ----------------
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 500
FPS = 60

display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Dragon Feast - Mystic Jungle")

clock = pygame.time.Clock()

# ---------------- GAME SETTINGS ----------------
PLAYER_STARTING_LIVES = 3
PLAYER_VELOCITY = 10

FOOD_STARTING_VELOCITY = 8
FOOD_ACCELERATION = 0.35
FOOD_MAX_VELOCITY = 24

WIN_SCORE = 25
BUFFER_DISTANCE = 350

PLAYER_MIN_Y = 100
PLAYER_MAX_Y = WINDOW_HEIGHT - 10
HUD_LINE_Y = 84

# Difficulty becomes noticeably faster as the score increases.
DIFFICULTY_TIERS = [
    (0, "EASY", 0.0),
    (5, "MEDIUM", 2.0),
    (12, "HARD", 4.0),
    (20, "INSANE", 6.0),
]

# ---------------- COLORS ----------------
# Premium fantasy palette: midnight blue + emerald + warm gold.
BG_TOP = (8, 15, 31)
BG_MIDDLE = (11, 35, 48)
BG_BOTTOM = (12, 61, 45)

DEEP_JUNGLE = (4, 15, 18)
JUNGLE = (8, 34, 35)
JUNGLE_LIGHT = (20, 72, 55)
JUNGLE_MID = (14, 53, 48)
MIST = (108, 166, 150)

WHITE = (242, 244, 235)
BLACK = (0, 0, 0)

GOLD = (238, 190, 72)
LIGHT_GOLD = (255, 225, 140)
GOLD_DARK = (128, 91, 35)
ORANGE = (224, 132, 58)

HEART_RED = (218, 58, 72)
HEART_DARK = (67, 27, 38)

CYAN = (105, 218, 205)
GREEN = (108, 211, 133)
PURPLE = (173, 130, 235)

HUD_BG = (6, 17, 28)
HUD_PANEL = (11, 29, 38)
HUD_BORDER = (74, 105, 91)

# ---------------- FONTS ----------------
# Clean premium fantasy typography.
# If a Cinzel font is placed beside the game, it will be used.
TITLE_FONT_FILE = "Cinzel-Bold.ttf"

try:
    title_font = pygame.font.Font(TITLE_FONT_FILE, 43)
    big_font = pygame.font.Font(TITLE_FONT_FILE, 38)
    main_font = pygame.font.Font(TITLE_FONT_FILE, 24)
    small_font = pygame.font.Font(TITLE_FONT_FILE, 16)
    tiny_font = pygame.font.Font(TITLE_FONT_FILE, 12)
except Exception:
    title_font = pygame.font.SysFont("georgia", 43, bold=True)
    big_font = pygame.font.SysFont("georgia", 38, bold=True)
    main_font = pygame.font.SysFont("georgia", 24, bold=True)
    small_font = pygame.font.SysFont("georgia", 16, bold=True)
    tiny_font = pygame.font.SysFont("trebuchet ms", 12, bold=True)

# ---------------- FILES ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIGH_SCORE_FILE = os.path.join(BASE_DIR, "score_data.json")

# ---------------- LOAD HIGH SCORE ----------------
def load_high_score():
    try:
        with open(HIGH_SCORE_FILE, "r") as file:
            return int(json.load(file).get("high_score", 0))
    except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError):
        return 0


def save_high_score(value):
    try:
        with open(HIGH_SCORE_FILE, "w") as file:
            json.dump({"high_score": int(value)}, file)
    except OSError:
        pass


high_score = load_high_score()

# ---------------- SOUND ----------------
sound_available = True

try:
    food_sound = pygame.mixer.Sound(os.path.join(BASE_DIR, "food_sound.wav"))
    miss_sound = pygame.mixer.Sound(os.path.join(BASE_DIR, "miss.wav"))
    miss_sound.set_volume(0.10)
    pygame.mixer.music.load(os.path.join(BASE_DIR, "background_music.wav"))
except pygame.error:
    sound_available = False

# ---------------- IMAGE HELPERS ----------------
def load_image(filename, fallback_size, fallback_color):
    path = os.path.join(BASE_DIR, filename)

    try:
        image = pygame.image.load(path).convert_alpha()
        return image
    except (pygame.error, FileNotFoundError):
        image = pygame.Surface(fallback_size, pygame.SRCALPHA)
        pygame.draw.ellipse(image, fallback_color, image.get_rect())
        return image


player_image = load_image("dragon.png", (110, 80), (190, 65, 45, 255))
food_image = load_image("food.png", (48, 48), (255, 180, 50, 255))

player_rect = player_image.get_rect()
player_rect.left = 30
player_rect.centery = WINDOW_HEIGHT // 2

food_rect = food_image.get_rect()
food_rect.x = WINDOW_WIDTH + BUFFER_DISTANCE
food_rect.y = random.randint(PLAYER_MIN_Y, WINDOW_HEIGHT - 55)

# ============================================================
# GAME STATE
# ============================================================

score = 0
player_lives = PLAYER_STARTING_LIVES
food_velocity = FOOD_STARTING_VELOCITY
difficulty_label = "EASY"

ultra_combo=0
ultra_best_combo=0
ultra_combo_timer=0
ultra_powerup=None
ultra_powerup_timer=0
ultra_powerup_cooldown=360
ultra_powerup_x=WINDOW_WIDTH+160
ultra_powerup_y=250
ultra_scene_tick=0
ultra_zone="MYSTIC FOREST"
ultra_zone_flash=0
ultra_event_timer=900
cinematic_transition_frames=0
cinematic_old_zone=""
cinematic_new_zone=""
cinematic_total_frames=150
ultra_event_name=""
ultra_achievement=""
ultra_achievement_timer=0
ultra_food_collected=0
ultra_powerups_collected=0
ultra_misses=0

is_new_high_score = False
is_game_paused = False
game_state = "menu"          # menu / playing / won / gameover

# Visual effects
particles = []
collect_flash = 0
difficulty_flash = 0
screen_shake = 0
last_difficulty = "EASY"
score_popups = []
menu_time = 0

# Decorative particles are deterministic/static so the recording stays clean.
ambient_particles = [
    (
        random.randint(20, WINDOW_WIDTH - 20),
        random.randint(105, WINDOW_HEIGHT - 60),
        random.randint(1, 3),
        random.random() * math.tau
    )
    for _ in range(55)
]


# ============================================================
# DIFFICULTY
# ============================================================

def get_difficulty_label(current_score):
    label = "EASY"

    for threshold, tier_label, _ in DIFFICULTY_TIERS:
        if current_score >= threshold:
            label = tier_label

    return label


def get_difficulty_bonus(current_score):
    bonus = 0.0

    for threshold, _, extra in DIFFICULTY_TIERS:
        if current_score >= threshold:
            bonus = extra

    return bonus


def get_progress_to_next_level(current_score):
    thresholds = [0, 5, 12, 20, WIN_SCORE]

    for i in range(len(thresholds) - 1):
        start = thresholds[i]
        end = thresholds[i + 1]

        if current_score < end:
            return start, end

    return WIN_SCORE, WIN_SCORE


# ============================================================
# TEXT / UI
# ============================================================

def draw_shadow_text(surface, text, font, position, text_color,
                     shadow_color=BLACK, shadow_offset=3):
    shadow = font.render(text, True, shadow_color)
    main_text = font.render(text, True, text_color)

    surface.blit(
        shadow,
        (position[0] + shadow_offset, position[1] + shadow_offset)
    )
    surface.blit(main_text, position)


def draw_centered_text(surface, text, font, center, color, shadow=True):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=center)

    if shadow:
        shadow_img = font.render(text, True, BLACK)
        surface.blit(
            shadow_img,
            (rect.x + 3, rect.y + 3)
        )

    surface.blit(rendered, rect)


# ============================================================
# HEARTS
# ============================================================

def draw_heart(surface, x, y, size=23, filled=True):
    color = HEART_RED if filled else HEART_DARK

    r = max(3, size // 3)

    pygame.draw.circle(
        surface, color,
        (x + size // 3, y + size // 3),
        r
    )

    pygame.draw.circle(
        surface, color,
        (x + (size * 2) // 3, y + size // 3),
        r
    )

    points = [
        (x + 1, y + size // 3),
        (x + size - 1, y + size // 3),
        (x + size // 2, y + size),
    ]

    pygame.draw.polygon(surface, color, points)

    if filled:
        # Tiny shine makes the hearts look more polished on recording.
        pygame.draw.circle(
            surface,
            (255, 175, 185),
            (x + size // 3 - 1, y + size // 3 - 2),
            2
        )


def draw_hearts(surface):
    start_x = WINDOW_WIDTH - 155

    for i in range(PLAYER_STARTING_LIVES):
        draw_heart(
            surface,
            start_x + i * 29,
            12,
            22,
            i < player_lives
        )


# ============================================================
# MYSTICAL JUNGLE BACKGROUND
# ============================================================

def draw_gradient_background(surface):
    # Three-stage cinematic gradient.
    for y in range(WINDOW_HEIGHT):
        t = y / WINDOW_HEIGHT

        if t < 0.55:
            p = t / 0.55
            c1, c2 = BG_TOP, BG_MIDDLE
        else:
            p = (t - 0.55) / 0.45
            c1, c2 = BG_MIDDLE, BG_BOTTOM

        r = int(c1[0] * (1 - p) + c2[0] * p)
        g = int(c1[1] * (1 - p) + c2[1] * p)
        b = int(c1[2] * (1 - p) + c2[2] * p)

        pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))


def draw_vines(surface):
    # Soft canopy silhouettes instead of repeated circular shapes.
    canopy = pygame.Surface((WINDOW_WIDTH, 145), pygame.SRCALPHA)

    for x in range(-80, WINDOW_WIDTH + 100, 115):
        pygame.draw.ellipse(
            canopy,
            (7, 27, 31, 235),
            (x, -30, 155, 95)
        )
        pygame.draw.ellipse(
            canopy,
            (12, 47, 40, 220),
            (x + 30, 25, 115, 70)
        )

    # Thin hanging vines.
    for x in (28, 105, 910, 970):
        pygame.draw.line(
            canopy,
            (32, 91, 66, 220),
            (x, 20),
            (x + 8, 132),
            3
        )
        for y in range(48, 125, 28):
            pygame.draw.ellipse(
                canopy,
                (46, 111, 76, 210),
                (x - 14, y, 22, 9)
            )

    surface.blit(canopy, (0, 84))


def draw_dragon_jungle(surface):
    # Distant mountains with a cleaner silhouette.
    mountain_points = [
        (0, 310), (130, 205), (230, 290),
        (350, 170), (465, 300),
        (590, 195), (705, 305),
        (825, 185), (1000, 300),
        (1000, WINDOW_HEIGHT), (0, WINDOW_HEIGHT)
    ]
    pygame.draw.polygon(surface, (8, 34, 40), mountain_points)

    # Moon / magical light source.
    moon_center = (835, 190)
    for radius, alpha in ((86, 18), (68, 25), (52, 255)):
        if radius == 52:
            pygame.draw.circle(surface, (205, 222, 188), moon_center, radius)
            pygame.draw.circle(surface, (178, 201, 170), (820, 175), 6)
            pygame.draw.circle(surface, (178, 201, 170), (855, 205), 4)
        else:
            glow = pygame.Surface((220, 220), pygame.SRCALPHA)
            pygame.draw.circle(
                glow,
                (185, 220, 185, alpha),
                (110, 110),
                radius
            )
            surface.blit(glow, (moon_center[0] - 110, moon_center[1] - 110))

    # Layered jungle silhouettes.
    for x, h in [(35, 145), (245, 110), (720, 125), (940, 160)]:
        pygame.draw.polygon(
            surface,
            (7, 28, 29),
            [
                (x - 55, 430),
                (x - 18, 430 - h),
                (x + 5, 430 - h - 30),
                (x + 30, 430 - h + 25),
                (x + 65, 430)
            ]
        )

    # Ancient stone pillars, darker and less distracting.
    for x in (145, 860):
        pygame.draw.rect(
            surface,
            (11, 45, 43),
            (x, 270, 23, 150)
        )
        pygame.draw.rect(
            surface,
            (20, 62, 54),
            (x - 9, 260, 41, 13)
        )
        pygame.draw.rect(
            surface,
            (20, 62, 54),
            (x - 6, 418, 35, 10)
        )

    # Low mist.
    mist = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    pygame.draw.ellipse(
        mist,
        (140, 190, 165, 18),
        (-140, 315, 650, 95)
    )
    pygame.draw.ellipse(
        mist,
        (140, 190, 165, 15),
        (420, 345, 720, 90)
    )
    surface.blit(mist, (0, 0))

def draw_ambient_particles(surface):
    for x, y, radius, phase in ambient_particles:
        glow = int(2 + 3 * (math.sin(pygame.time.get_ticks() * 0.002 + phase) + 1))

        pygame.draw.circle(
            surface,
            (145, 220, 150),
            (x, y),
            radius + glow // 3
        )


def draw_background(surface):
    global ultra_scene_tick
    # Keep the old environment visually frozen during the cinematic transition.
    if cinematic_transition_frames <= 0:
        ultra_scene_tick += 1

    themes = {
        "MYSTIC FOREST": ((7,16,31),(12,42,43),(20,74,50),(10,36,44),(11,57,45),(5,25,28),(100,220,170),(145,210,180)),
        "DRAGON VALLEY": ((25,12,28),(76,30,36),(116,67,34),(56,25,36),(78,38,31),(34,18,23),(255,154,76),(245,190,150)),
        "SHADOW JUNGLE": ((11,8,30),(42,20,68),(52,37,70),(29,18,48),(43,27,52),(16,15,31),(184,128,255),(190,170,220)),
    }
    top, mid, bottom, far, midc, near, accent, mistc = themes.get(ultra_zone, themes["MYSTIC FOREST"])

    # Cinematic zone gradient.
    for y in range(WINDOW_HEIGHT):
        q=y/(WINDOW_HEIGHT-1)
        if q < 0.55:
            f=q/0.55; c1,c2=top,mid
        else:
            f=(q-0.55)/0.45; c1,c2=mid,bottom
        c=tuple(int(c1[i]*(1-f)+c2[i]*f) for i in range(3))
        pygame.draw.line(surface,c,(0,y),(WINDOW_WIDTH,y))

    scroll1=(ultra_scene_tick*0.45)%170
    scroll2=(ultra_scene_tick*0.9)%130
    scroll3=(ultra_scene_tick*1.5)%105

    # Far parallax mountains.
    for x in range(-180, WINDOW_WIDTH+200, 170):
        xx=x-scroll1; peak=180+int(20*math.sin(x*0.03))
        pygame.draw.polygon(surface,far,[(xx,330),(xx+85,peak),(xx+170,330)])

    if ultra_zone == "MYSTIC FOREST":
        for x in range(-110, WINDOW_WIDTH+170, 125):
            xx=x-scroll2
            pygame.draw.ellipse(surface,midc,(xx,205,95,150))
            pygame.draw.rect(surface,near,(xx+36,285,22,135),border_radius=8)
            pygame.draw.ellipse(surface,(27,88,65),(xx+10,188,58,75))
        for i in range(26):
            x=(i*91+ultra_scene_tick*0.35)%WINDOW_WIDTH
            y=130+(i*43)%240
            pygame.draw.circle(surface,accent,(int(x),int(y)),1+(i%4==0))

    elif ultra_zone == "DRAGON VALLEY":
        pygame.draw.polygon(surface,midc,[(0,400),(115,265),(205,320),(300,235),(380,350),(410,500),(0,500)])
        pygame.draw.polygon(surface,midc,[(1000,400),(885,255),(800,320),(715,235),(630,350),(590,500),(1000,500)])
        pygame.draw.polygon(surface,(45,17,25),[(280,500),(410,305),(500,215),(600,315),(720,500)])
        for i in range(34):
            x=(i*53+ultra_scene_tick*1.6)%WINDOW_WIDTH
            y=(410-(ultra_scene_tick*1.7+i*19)%300)
            pygame.draw.circle(surface,accent,(int(x),int(y)),1+(i%3==0))

    elif ultra_zone == "SHADOW JUNGLE":
        moon=(800,160)
        glow=pygame.Surface((180,180),pygame.SRCALPHA)
        pygame.draw.circle(glow,(*accent,24),(90,90),72)
        pygame.draw.circle(glow,(*accent,35),(90,90),55)
        surface.blit(glow,(moon[0]-90,moon[1]-90))
        pygame.draw.circle(surface,(215,205,235),moon,38)
        for x in range(-90,WINDOW_WIDTH+170,108):
            xx=x-scroll3
            pygame.draw.polygon(surface,near,[(xx+35,420),(xx+63,165),(xx+90,420)])
            pygame.draw.polygon(surface,midc,[(xx+5,420),(xx+40,235),(xx+70,420)])
        for i in range(20):
            x=(i*99+ultra_scene_tick*0.8)%WINDOW_WIDTH
            y=155+(i*31)%220
            pygame.draw.circle(surface,accent,(int(x),int(y)),2)

    else:
        # Ancient Temple is a completely different silhouette.
        pygame.draw.rect(surface,far,(285,192,430,228))
        pygame.draw.rect(surface,midc,(350,168,72,252))
        pygame.draw.rect(surface,midc,(578,168,72,252))
        pygame.draw.polygon(surface,midc,[(322,195),(678,195),(625,122),(375,122)])
        pygame.draw.rect(surface,(15,13,19),(455,235,90,185))
        for x in (402,598):
            glow=pygame.Surface((110,110),pygame.SRCALPHA)
            a=42+int(10*math.sin(ultra_scene_tick*0.12+x))
            pygame.draw.circle(glow,(*accent,a),(55,55),35)
            surface.blit(glow,(x-55,215))
            pygame.draw.circle(surface,accent,(x,270),7)

    # Fast world streaks at higher difficulty.
    if difficulty_label in ("HARD","INSANE"):
        for i in range(22):
            y=110+(i*31)%320
            x=(i*93+ultra_scene_tick*4.5)%WINDOW_WIDTH
            pygame.draw.line(surface,accent,(int(x),y),(int(x+28),y),1)

    # Perspective ground lane to create a runner-game feel.
    pygame.draw.polygon(surface,near,[(0,422),(225,420),(500,395),(775,420),(1000,422),(1000,500),(0,500)])
    for lane in (300,500,700):
        dash_offset=(ultra_scene_tick*3)%60
        for k in range(7):
            y1=425+k*22+dash_offset
            y2=y1+10
            if y1<500:
                pygame.draw.line(surface,(55,75,67),(lane,y1),(lane,y2),2)

    mist=pygame.Surface((WINDOW_WIDTH,135),pygame.SRCALPHA)
    pygame.draw.ellipse(mist,(*mistc,22),(-150,38,650,88))
    pygame.draw.ellipse(mist,(*mistc,17),(450,15,720,95))
    surface.blit(mist,(0,365))


# ============================================================
# HUD
# ============================================================

def draw_hud(surface):
    # Clean premium top bar.
    pygame.draw.rect(
        surface,
        HUD_BG,
        (0, 0, WINDOW_WIDTH, HUD_LINE_Y)
    )

    pygame.draw.line(
        surface,
        GOLD_DARK,
        (0, HUD_LINE_Y),
        (WINDOW_WIDTH, HUD_LINE_Y),
        2
    )

    # Score card.
    score_card = pygame.Rect(14, 10, 160, 54)
    pygame.draw.rect(surface, HUD_PANEL, score_card, border_radius=12)
    pygame.draw.rect(surface, HUD_BORDER, score_card, 1, border_radius=12)

    draw_shadow_text(
        surface,
        f"SCORE  {score}",
        main_font,
        (27, 17),
        WHITE,
        shadow_color=(0, 0, 0)
    )

    draw_shadow_text(
        surface,
        f"BEST  {high_score}",
        tiny_font,
        (28, 45),
        LIGHT_GOLD
    )

    # Title.
    zone_label = tiny_font.render(ultra_zone, True, MIST)
    surface.blit(zone_label, zone_label.get_rect(center=(WINDOW_WIDTH // 2, 61)))

    title = title_font.render("DRAGON FEAST", True, LIGHT_GOLD)
    title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 30))

    # Very subtle gold outline/shadow.
    shadow = title_font.render("DRAGON FEAST", True, (77, 57, 25))
    surface.blit(shadow, (title_rect.x + 2, title_rect.y + 2))
    surface.blit(title, title_rect)

    # Small subtitle for adventure identity.
    subtitle = tiny_font.render(
        "THE MYSTIC JUNGLE",
        True,
        MIST
    )
    surface.blit(
        subtitle,
        subtitle.get_rect(center=(WINDOW_WIDTH // 2, 60))
    )

    # Lives card.
    lives_card = pygame.Rect(WINDOW_WIDTH - 176, 10, 162, 54)
    pygame.draw.rect(surface, HUD_PANEL, lives_card, border_radius=12)
    pygame.draw.rect(surface, HUD_BORDER, lives_card, 1, border_radius=12)

    lives_label = tiny_font.render("LIVES", True, MIST)
    surface.blit(lives_label, (WINDOW_WIDTH - 162, 15))

    for i in range(PLAYER_STARTING_LIVES):
        draw_heart(
            surface,
            WINDOW_WIDTH - 158 + i * 28,
            31,
            20,
            i < player_lives
        )

    # Difficulty pill.
    badge_width = 118
    badge_rect = pygame.Rect(
        WINDOW_WIDTH // 2 - badge_width // 2,
        48,
        badge_width,
        22
    )

    difficulty_color = {
        "EASY": GREEN,
        "MEDIUM": LIGHT_GOLD,
        "HARD": ORANGE,
        "INSANE": HEART_RED
    }.get(difficulty_label, WHITE)

    pygame.draw.rect(
        surface,
        (13, 34, 35),
        badge_rect,
        border_radius=11
    )
    pygame.draw.rect(
        surface,
        difficulty_color,
        badge_rect,
        1,
        border_radius=11
    )

    diff_text = tiny_font.render(
        f" {difficulty_label} ",
        True,
        difficulty_color
    )
    surface.blit(
        diff_text,
        diff_text.get_rect(center=badge_rect.center)
    )

    # Target progress bar.
    progress_x = WINDOW_WIDTH // 2 - 155
    progress_y = 74
    progress_w = 310
    progress_h = 5

    pygame.draw.rect(
        surface,
        (32, 49, 45),
        (progress_x, progress_y, progress_w, progress_h),
        border_radius=3
    )

    progress = min(score / WIN_SCORE, 1.0)

    pygame.draw.rect(
        surface,
        GOLD,
        (
            progress_x,
            progress_y,
            int(progress_w * progress),
            progress_h
        ),
        border_radius=3
    )

    target_text = tiny_font.render(
        f"FEAST TARGET  {WIN_SCORE}",
        True,
        MIST
    )
    surface.blit(
        target_text,
        target_text.get_rect(
            center=(WINDOW_WIDTH // 2, 78)
        )
    )


# ============================================================
# ULTRA FEATURES
# ============================================================

def start_cinematic_zone_transition(old_zone,new_zone):
    global cinematic_transition_frames,cinematic_old_zone,cinematic_new_zone
    cinematic_old_zone=old_zone
    cinematic_new_zone=new_zone
    cinematic_transition_frames=cinematic_total_frames


def cinematic_ease(t):
    t=max(0.0,min(1.0,t))
    return 1-(1-t)**3


def draw_cinematic_transition(surface):
    if cinematic_transition_frames<=0:
        return

    elapsed=cinematic_total_frames-cinematic_transition_frames
    p=elapsed/cinematic_total_frames

    # Letterbox bars + dark cinematic veil.
    bar=int(34*math.sin(p*math.pi))
    pygame.draw.rect(surface,(2,7,12),(0,0,WINDOW_WIDTH,bar))
    pygame.draw.rect(surface,(2,7,12),(0,WINDOW_HEIGHT-bar,WINDOW_WIDTH,bar))

    alpha=int(225*math.sin(p*math.pi))
    veil=pygame.Surface((WINDOW_WIDTH,WINDOW_HEIGHT),pygame.SRCALPHA)
    veil.fill((1,5,10,max(0,alpha)))
    surface.blit(veil,(0,0))

    # Slowly reveal the destination title, then remove it before the reveal.
    if p < 0.72:
        fade_in=min(1.0,p/0.22)
        fade_out=min(1.0,max(0.0,(0.72-p)/0.22))
        text_alpha=int(255*min(fade_in, fade_out if p>0.50 else fade_in))

        q=cinematic_ease(min(1.0,p/0.55))
        y=int(315-85*q)

        small=tiny_font.render("ENTERING",True,MIST)
        name=main_font.render(cinematic_new_zone,True,LIGHT_GOLD)
        small.set_alpha(text_alpha)
        name.set_alpha(text_alpha)

        glow=pygame.Surface((520,130),pygame.SRCALPHA)
        pygame.draw.ellipse(
            glow,(238,190,72,max(0,int(28*text_alpha/255))),(80,38,360,42)
        )
        surface.blit(glow,(WINDOW_WIDTH//2-260,y-65))
        surface.blit(small,small.get_rect(center=(WINDOW_WIDTH//2,y-28)))
        surface.blit(name,name.get_rect(center=(WINDOW_WIDTH//2,y+10)))

        line=int(300*math.sin(min(1.0,max(0.0,(p-0.18)/0.40))*math.pi))
        if line>0:
            pygame.draw.line(
                surface,GOLD,
                (WINDOW_WIDTH//2-line//2,y+42),
                (WINDOW_WIDTH//2+line//2,y+42),2
            )

    # Warm flash masks the exact moment the new environment is revealed.
    if p>0.82:
        a=int(85*(1-(p-0.82)/0.18))
        flash=pygame.Surface((WINDOW_WIDTH,WINDOW_HEIGHT),pygame.SRCALPHA)
        flash.fill((255,225,150,max(0,a)))
        surface.blit(flash,(0,0))


def update_cinematic_transition():
    global cinematic_transition_frames, ultra_zone, ultra_zone_flash

    if cinematic_transition_frames <= 0:
        return

    cinematic_transition_frames -= 1

    # Only now does the new environment become active.
    if cinematic_transition_frames == 0:
        ultra_zone=cinematic_new_zone
        ultra_zone_flash=0


def ultra_zone_for_score(v):
    if v>=15: return "SHADOW JUNGLE"
    if v>=8: return "DRAGON VALLEY"
    return "MYSTIC FOREST"

def ultra_unlock(text):
    global ultra_achievement, ultra_achievement_timer
    ultra_achievement=text; ultra_achievement_timer=100

def ultra_spawn_powerup():
    global ultra_powerup, ultra_powerup_cooldown, ultra_powerup_x, ultra_powerup_y
    ultra_powerup=random.choice(["SHIELD","FRENZY","MAGNET","HEART"])
    ultra_powerup_x=WINDOW_WIDTH+random.randint(120,260)
    ultra_powerup_y=random.randint(PLAYER_MIN_Y+25,WINDOW_HEIGHT-85)
    ultra_powerup_cooldown=random.randint(420,620)

def ultra_draw_powerup(surface):
    if ultra_powerup is None: return
    x=int(ultra_powerup_x); y=int(ultra_powerup_y+math.sin(pygame.time.get_ticks()*0.009)*5)
    colors={"SHIELD":(90,200,240),"FRENZY":(245,170,70),"MAGNET":(190,125,240),"HEART":(235,75,100)}
    labels={"SHIELD":"S","FRENZY":"2X","MAGNET":"M","HEART":"+"}
    c=colors[ultra_powerup]
    glow=pygame.Surface((86,86),pygame.SRCALPHA)
    pygame.draw.circle(glow,(*c,36),(43,43),34)
    pygame.draw.circle(glow,(*c,16),(43,43),41)
    surface.blit(glow,(x-43,y-43))
    pygame.draw.circle(surface,(7,22,30),(x,y),22)
    pygame.draw.circle(surface,c,(x,y),22,2)
    t=small_font.render(labels[ultra_powerup],True,c)
    surface.blit(t,t.get_rect(center=(x,y)))

def ultra_draw_overlays(surface):
    # Show combo only for a genuine 3+ catch streak.
    if ultra_combo>=3 and ultra_combo_timer>0:
        draw_centered_text(surface,f"🔥 COMBO x{ultra_combo}",small_font,(WINDOW_WIDTH//2,103),LIGHT_GOLD)

    if ultra_powerup_timer>0:
        powerup_labels={
            "SHIELD":"🛡️ SHIELD READY",
            "FRENZY":"🔥 2X FRENZY",
            "MAGNET":"🧲 MAGNET ACTIVE"
        }
        label=powerup_labels.get(ultra_powerup,"")
        if label:
            draw_centered_text(
                surface,f"{label}  {max(1,ultra_powerup_timer//FPS+1)}s",
                tiny_font,(WINDOW_WIDTH//2,120),CYAN
            )
    if ultra_zone_flash>0:
        panel=pygame.Rect(WINDOW_WIDTH//2-185,130,370,62); pygame.draw.rect(surface,(5,16,25),panel,border_radius=17); pygame.draw.rect(surface,GOLD,panel,2,border_radius=17)
        draw_centered_text(surface,"NEW ZONE",tiny_font,(WINDOW_WIDTH//2,148),MIST); draw_centered_text(surface,ultra_zone,main_font,(WINDOW_WIDTH//2,174),LIGHT_GOLD)
    if ultra_achievement_timer>0:
        panel=pygame.Rect(WINDOW_WIDTH-315,102,295,64); pygame.draw.rect(surface,(7,21,29),panel,border_radius=16); pygame.draw.rect(surface,GOLD,panel,2,border_radius=16)
        draw_centered_text(surface,"ACHIEVEMENT UNLOCKED",tiny_font,(panel.centerx,122),LIGHT_GOLD); draw_centered_text(surface,ultra_achievement,small_font,(panel.centerx,147),WHITE)
    if ultra_event_timer>0 and score>=8:
        tint=pygame.Surface((WINDOW_WIDTH,WINDOW_HEIGHT),pygame.SRCALPHA); tint.fill((70,25,75,20)); surface.blit(tint,(0,0))
        if ultra_event_timer>7*FPS-80: draw_centered_text(surface,ultra_event_name,main_font,(WINDOW_WIDTH//2,110),LIGHT_GOLD)

def ultra_draw_stats(surface):
    ov=pygame.Surface((WINDOW_WIDTH,WINDOW_HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,185)); surface.blit(ov,(0,0))
    panel=pygame.Rect(WINDOW_WIDTH//2-265,62,530,370); pygame.draw.rect(surface,(5,16,25),panel,border_radius=24); pygame.draw.rect(surface,GOLD,panel,2,border_radius=24)
    draw_centered_text(surface,"ADVENTURE COMPLETE",big_font,(WINDOW_WIDTH//2,108),LIGHT_GOLD); draw_centered_text(surface,"DRAGON FEAST • ULTRA EDITION",tiny_font,(WINDOW_WIDTH//2,140),MIST)
    stats=[("FINAL SCORE",score),("BEST SCORE",high_score),("FOOD",ultra_food_collected),("BEST COMBO",ultra_best_combo),("POWER-UPS",ultra_powerups_collected),("MISSES",ultra_misses)]
    for i,(label,val) in enumerate(stats):
        col=i//3; row=i%3; x=panel.x+140+col*250; y=195+row*57; draw_centered_text(surface,str(val),main_font,(x,y),GOLD); draw_centered_text(surface,label,tiny_font,(x,y+22),MIST)
    draw_centered_text(surface,"PRESS R TO PLAY AGAIN",small_font,(WINDOW_WIDTH//2,396),WHITE)

def ultra_update():
    global ultra_combo_timer,ultra_combo,ultra_powerup_timer,ultra_powerup_cooldown
    global ultra_zone,ultra_zone_flash,ultra_event_timer,ultra_event_name
    global ultra_achievement_timer

    # During a cinematic transition, only the cinematic clock advances.
    if cinematic_transition_frames > 0:
        update_cinematic_transition()
        return

    if ultra_combo_timer>0: ultra_combo_timer-=1
    else: ultra_combo=0

    if ultra_powerup_timer>0: ultra_powerup_timer-=1

    if ultra_powerup_cooldown>0:
        ultra_powerup_cooldown-=1
    elif ultra_powerup is None:
        ultra_spawn_powerup()

    nz=ultra_zone_for_score(score)
    if nz!=ultra_zone:
        old_zone=ultra_zone
        ultra_zone_flash=0
        start_cinematic_zone_transition(old_zone,nz)
        # Keep ultra_zone unchanged until the cinematic reveal completes.
    elif ultra_zone_flash>0:
        ultra_zone_flash-=1

    if ultra_achievement_timer>0:
        ultra_achievement_timer-=1

    if ultra_event_timer>0:
        ultra_event_timer-=1
    elif score>=8:
        ultra_event_name=random.choice([
            "THE JUNGLE AWAKENS",
            "SURVIVE THE STORM",
            "ANCIENT MAGIC RISES"
        ])
        ultra_event_timer=7*FPS


# ============================================================
# SCORE POPUPS
# ============================================================

def spawn_score_popup(x, y):
    score_popups.append({
        "x": float(x),
        "y": float(y),
        "life": 42,
        "max_life": 42
    })


def update_score_popups():
    for popup in score_popups[:]:
        popup["y"] -= 0.8
        popup["life"] -= 1
        if popup["life"] <= 0:
            score_popups.remove(popup)


def draw_score_popups(surface):
    for popup in score_popups:
        alpha = int(255 * popup["life"] / popup["max_life"])
        img = pygame.Surface((180, 45), pygame.SRCALPHA)
        shadow = main_font.render("+1 FEAST!", True, (0, 0, 0))
        text = main_font.render("+1 FEAST!", True, LIGHT_GOLD)
        shadow.set_alpha(alpha)
        text.set_alpha(alpha)
        img.blit(shadow, (3, 3))
        img.blit(text, (0, 0))
        rect = img.get_rect(center=(int(popup["x"]), int(popup["y"])))
        surface.blit(img, rect)


# ============================================================
# CINEMATIC START SCREEN
# ============================================================

def draw_start_screen(surface):
    global menu_time
    menu_time += 1

    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((2, 7, 16, 125))
    surface.blit(overlay, (0, 0))

    # Floating magical motes.
    for i in range(22):
        a = menu_time * 0.006 + i * 0.57
        radius = 125 + (i % 5) * 22
        x = WINDOW_WIDTH // 2 + math.cos(a) * radius
        y = 235 + math.sin(a * 1.2) * 85
        pygame.draw.circle(surface, (238, 190, 72), (int(x), int(y)), 2)

    panel = pygame.Rect(WINDOW_WIDTH // 2 - 285, 105, 570, 315)
    pygame.draw.rect(surface, (5, 16, 27), panel, border_radius=26)
    pygame.draw.rect(surface, (124, 99, 54), panel, 2, border_radius=26)

    pygame.draw.circle(surface, (24, 63, 56), (WINDOW_WIDTH // 2, 150), 29)
    pygame.draw.circle(surface, GOLD, (WINDOW_WIDTH // 2, 150), 29, 2)

    draw_centered_text(surface, "DRAGON FEAST", title_font,
                       (WINDOW_WIDTH // 2, 205), LIGHT_GOLD)
    draw_centered_text(surface, "THE MYSTIC JUNGLE", small_font,
                       (WINDOW_WIDTH // 2, 242), MIST)
    draw_centered_text(surface, "FEED THE DRAGON  •  SURVIVE  •  REACH 25",
                       tiny_font, (WINDOW_WIDTH // 2, 276), WHITE)

    pulse = int(3 * math.sin(menu_time * 0.08))
    button = pygame.Rect(WINDOW_WIDTH // 2 - 145 - pulse, 306 - pulse // 2,
                         290 + pulse * 2, 48 + pulse)
    pygame.draw.rect(surface, (28, 70, 57), button, border_radius=15)
    pygame.draw.rect(surface, GOLD, button, 2, border_radius=15)
    draw_centered_text(surface, "PRESS ENTER TO START", small_font,
                       button.center, WHITE)
    draw_centered_text(surface, "↑ ↓ / W S  MOVE", tiny_font,
                       (WINDOW_WIDTH // 2, 385), MIST, shadow=False)


# ============================================================
# FOOD COLLECTION PARTICLES
# ============================================================

def spawn_collect_particles(x, y):
    global collect_flash, screen_shake

    collect_flash = 10
    screen_shake = 5

    for _ in range(18):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1.5, 5.0)

        particles.append({
            "x": x,
            "y": y,
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed,
            "life": random.randint(18, 35),
            "max_life": 35,
            "size": random.randint(2, 5)
        })


def update_particles():
    for particle in particles[:]:
        particle["x"] += particle["vx"]
        particle["y"] += particle["vy"]
        particle["vy"] += 0.06
        particle["life"] -= 1

        if particle["life"] <= 0:
            particles.remove(particle)


def draw_particles(surface):
    for particle in particles:
        alpha = int(
            255 * particle["life"] / particle["max_life"]
        )

        particle_surface = pygame.Surface(
            (12, 12),
            pygame.SRCALPHA
        )

        pygame.draw.circle(
            particle_surface,
            (255, 215, 80, alpha),
            (6, 6),
            particle["size"]
        )

        surface.blit(
            particle_surface,
            (
                int(particle["x"] - 6),
                int(particle["y"] - 6)
            )
        )


def draw_collect_flash(surface):
    if collect_flash <= 0:
        return

    alpha = min(130, collect_flash * 13)

    flash = pygame.Surface(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.SRCALPHA
    )
    flash.fill((255, 220, 90, alpha))
    surface.blit(flash, (0, 0))


# ============================================================
# RESET / STATE
# ============================================================

def reset_food():
    food_rect.x = WINDOW_WIDTH + BUFFER_DISTANCE
    food_rect.y = random.randint(
        PLAYER_MIN_Y,
        WINDOW_HEIGHT - 55
    )


def reset_game():
    global score
    global player_lives
    global food_velocity
    global difficulty_label
    global is_new_high_score
    global game_state
    global last_difficulty
    global collect_flash
    global difficulty_flash
    global screen_shake
    global particles
    global score_popups

    score = 0
    ultra_combo=0; ultra_best_combo=0; ultra_combo_timer=0; ultra_powerup=None; ultra_powerup_timer=0; ultra_powerup_cooldown=360; ultra_powerup_x=WINDOW_WIDTH+160; ultra_powerup_y=250; ultra_scene_tick=0; ultra_zone="MYSTIC FOREST"; ultra_zone_flash=0; ultra_event_timer=900; ultra_event_name=""; ultra_achievement=""; ultra_achievement_timer=0; ultra_food_collected=0; ultra_powerups_collected=0; ultra_misses=0; cinematic_transition_frames=0; cinematic_old_zone=""; cinematic_new_zone=""
    player_lives = PLAYER_STARTING_LIVES
    food_velocity = FOOD_STARTING_VELOCITY
    difficulty_label = "EASY"
    last_difficulty = "EASY"

    is_new_high_score = False
    game_state = "playing"

    collect_flash = 0
    difficulty_flash = 0
    screen_shake = 0
    particles.clear()
    score_popups.clear()

    player_rect.centery = WINDOW_HEIGHT // 2
    reset_food()


def check_high_score():
    global high_score
    global is_new_high_score

    if score > high_score:
        high_score = score
        is_new_high_score = True


# ============================================================
# OVERLAY SCREENS
# ============================================================

def draw_panel(surface, rect):
    panel = pygame.Surface(
        (rect.width, rect.height),
        pygame.SRCALPHA
    )

    pygame.draw.rect(
        panel,
        (3, 12, 15, 225),
        panel.get_rect(),
        border_radius=20
    )

    pygame.draw.rect(
        panel,
        (255, 220, 100, 150),
        panel.get_rect(),
        2,
        border_radius=20
    )

    surface.blit(panel, rect.topleft)


def draw_controls(surface):
    # Small clean instruction bar for recording.
    rect = pygame.Rect(
        WINDOW_WIDTH // 2 - 215,
        WINDOW_HEIGHT - 35,
        430,
        24
    )

    pygame.draw.rect(
        surface,
        (5, 18, 22),
        rect,
        border_radius=12
    )

    pygame.draw.rect(
        surface,
        (55, 91, 79),
        rect,
        1,
        border_radius=12
    )

    text = tiny_font.render(
        "↑ ↓ / W S  MOVE     •     P  PAUSE     •     ESC  QUIT",
        True,
        WHITE
    )

    surface.blit(
        text,
        text.get_rect(center=rect.center)
    )


def draw_game_over(surface):
    # Dark overlay
    overlay = pygame.Surface(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.SRCALPHA
    )
    overlay.fill((0, 0, 0, 195))
    surface.blit(overlay, (0, 0))

    # Game Over panel
    panel = pygame.Rect(
        WINDOW_WIDTH // 2 - 290,
        80,
        580,
        410
    )
    draw_panel(surface, panel)

    # Main title
    draw_centered_text(
        surface,
        "OH NO, DRAGON!",
        big_font,
        (WINDOW_WIDTH // 2, 125),
        HEART_RED
    )

    # Explanation
    draw_centered_text(
        surface,
        "ALL 3 LIVES ARE GONE!",
        main_font,
        (WINDOW_WIDTH // 2, 180),
        WHITE
    )

    draw_centered_text(
        surface,
        "Your hearts have run out...",
        small_font,
        (WINDOW_WIDTH // 2, 220),
        MIST
    )

    draw_centered_text(
        surface,
        "The dragon needs a little rest!",
        small_font,
        (WINDOW_WIDTH // 2, 250),
        MIST
    )

    # Final score
    draw_centered_text(
        surface,
        f"FINAL SCORE   {score}",
        main_font,
        (WINDOW_WIDTH // 2, 295),
        WHITE
    )

    # Best score / high score
    draw_centered_text(
        surface,
        f"BEST SCORE   {high_score}",
        small_font,
        (WINDOW_WIDTH // 2, 330),
        LIGHT_GOLD
    )

    # New high score message
    if is_new_high_score:
        draw_centered_text(
            surface,
            "NEW HIGH SCORE!",
            main_font,
            (WINDOW_WIDTH // 2, 365),
            GOLD
        )


    # Restart button.
    button = pygame.Rect(
        WINDOW_WIDTH // 2 - 135,
        325,
        270,
        45
    )

    pygame.draw.rect(
        surface,
        (70, 105, 55),
        button,
        border_radius=14
    )
    pygame.draw.rect(
        surface,
        GOLD,
        button,
        2,
        border_radius=14
    )

    draw_centered_text(
        surface,
        "PRESS R TO RESTART",
        small_font,
        button.center,
        WHITE
    )


def draw_win_screen(surface):
    overlay = pygame.Surface(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.SRCALPHA
    )
    overlay.fill((2, 8, 12, 165))
    surface.blit(overlay, (0, 0))

    panel = pygame.Rect(
        WINDOW_WIDTH // 2 - 260,
        90,
        520,
        320
    )
    draw_panel(surface, panel)

    draw_centered_text(
        surface,
        "YOU WIN!",
        big_font,
        (WINDOW_WIDTH // 2, 145),
        GOLD
    )

    draw_centered_text(
        surface,
        "DRAGON FEAST COMPLETE",
        main_font,
        (WINDOW_WIDTH // 2, 200),
        LIGHT_GOLD
    )

    draw_centered_text(
        surface,
        f"TARGET REACHED   {score} / {WIN_SCORE}",
        small_font,
        (WINDOW_WIDTH // 2, 240),
        WHITE
    )

    if is_new_high_score:
        draw_centered_text(
            surface,
            "NEW HIGH SCORE!",
            main_font,
            (WINDOW_WIDTH // 2, 280),
            GOLD
        )

    button = pygame.Rect(
        WINDOW_WIDTH // 2 - 145,
        325,
        290,
        45
    )

    pygame.draw.rect(
        surface,
        (65, 105, 60),
        button,
        border_radius=14
    )
    pygame.draw.rect(
        surface,
        GOLD,
        button,
        2,
        border_radius=14
    )

    draw_centered_text(
        surface,
        "PRESS R / ANY KEY TO PLAY AGAIN",
        small_font,
        button.center,
        WHITE
    )


def draw_pause_screen(surface):
    overlay = pygame.Surface(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.SRCALPHA
    )
    overlay.fill((0, 0, 0, 140))
    surface.blit(overlay, (0, 0))

    draw_centered_text(
        surface,
        "PAUSED",
        big_font,
        (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20),
        LIGHT_GOLD
    )

    draw_centered_text(
        surface,
        "PRESS P TO CONTINUE",
        small_font,
        (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 35),
        WHITE
    )


# ============================================================
# DRAW WORLD
# ============================================================

def draw_game():
    global screen_shake

    draw_background(display_surface)

    # Fade the HUD out during the cinematic, then restore it with the new zone.
    if cinematic_transition_frames > 0:
        hud_layer=pygame.Surface((WINDOW_WIDTH,HUD_LINE_Y),pygame.SRCALPHA)
        draw_hud(hud_layer)
        elapsed=cinematic_total_frames-cinematic_transition_frames
        p=elapsed/cinematic_total_frames
        hud_alpha=max(0,int(255*(1-min(1.0,p/0.38))))
        hud_layer.set_alpha(hud_alpha)
        display_surface.blit(hud_layer,(0,0))
    else:
        draw_hud(display_surface)

    if ultra_zone_flash > 0:
        flash=pygame.Surface((WINDOW_WIDTH,WINDOW_HEIGHT),pygame.SRCALPHA)
        flash.fill((255,220,120,min(90,int(ultra_zone_flash*0.9))))
        display_surface.blit(flash,(0,0))

    # Shake only the playfield objects, not the HUD.
    shake_x = random.randint(-screen_shake, screen_shake) if screen_shake else 0
    shake_y = random.randint(-screen_shake, screen_shake) if screen_shake else 0

    display_surface.blit(
        player_image,
        (
            player_rect.x + shake_x,
            player_rect.y + shake_y
        )
    )

    display_surface.blit(
        food_image,
        (
            food_rect.x + shake_x,
            food_rect.y + shake_y
        )
    )

    ultra_draw_powerup(display_surface)
    draw_particles(display_surface)
    draw_score_popups(display_surface)
    draw_collect_flash(display_surface)

    # Difficulty change notification.
    if difficulty_flash > 0:
        draw_centered_text(
            display_surface,
            f"{difficulty_label}!",
            main_font,
            (WINDOW_WIDTH // 2, 115),
            GOLD
        )

    ultra_draw_overlays(display_surface)
    draw_controls(display_surface)
    draw_cinematic_transition(display_surface)


# ============================================================
# START MUSIC
# ============================================================

if sound_available:
    try:
        pygame.mixer.music.play(-1, 0.0)
    except pygame.error:
        pass


# ============================================================
# MAIN LOOP
# ============================================================

running = True

while running:

    # ---------------- EVENTS ----------------
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:
                running = False

            elif event.key == pygame.K_p and game_state == "playing":
                is_game_paused = not is_game_paused

                if sound_available:
                    try:
                        if is_game_paused:
                            pygame.mixer.music.pause()
                        else:
                            pygame.mixer.music.unpause()
                    except pygame.error:
                        pass

            elif game_state == "menu":
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    reset_game()
                    if sound_available:
                        try:
                            pygame.mixer.music.play(-1, 0.0)
                        except pygame.error:
                            pass

            elif game_state == "gameover":
               if event.key == pygame.K_r:
                    reset_game()

            elif game_state == "won":
                if event.key == pygame.K_r:
                    reset_game()

                    if sound_available:
                        try:
                            pygame.mixer.music.play(-1, 0.0)
                        except pygame.error:
                            pass

    # ---------------- START SCREEN ----------------
    if game_state == "menu":
        draw_background(display_surface)
        draw_hud(display_surface)
        draw_start_screen(display_surface)
        pygame.display.update()
        clock.tick(FPS)
        continue

    # ---------------- PAUSED ----------------
    if is_game_paused:
        draw_game()
        draw_pause_screen(display_surface)
        pygame.display.update()
        clock.tick(FPS)
        continue

    # ---------------- END SCREENS ----------------
    if game_state == "gameover":
        draw_game()
        draw_game_over(display_surface)
        pygame.display.update()
        clock.tick(FPS)
        continue

    if game_state == "won":
        draw_game()
        draw_win_screen(display_surface)
        pygame.display.update()
        clock.tick(FPS)
        continue

    # ---------------- GAMEPLAY MOVEMENT ----------------
    # True cinematic freeze: dragon, food and power-ups do not move.
    if cinematic_transition_frames <= 0:
        # ---------------- PLAYER MOVEMENT ----------------
        keys = pygame.key.get_pressed()

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            if player_rect.top > PLAYER_MIN_Y:
                player_rect.y -= PLAYER_VELOCITY

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            if player_rect.bottom < PLAYER_MAX_Y:
                player_rect.y += PLAYER_VELOCITY

        # ---------------- FOOD MOVEMENT ----------------
        if food_rect.x < -food_rect.width:
            ultra_misses += 1
            ultra_combo=0
            if ultra_powerup=="SHIELD" and ultra_powerup_timer>0:
                ultra_powerup_timer=0
            else:
                player_lives -= 1

            if sound_available:
                try:
                    miss_sound.play()
                except pygame.error:
                    pass

            reset_food()

            if player_lives <= 0:
                game_state = "gameover"

                if is_new_high_score:
                    save_high_score(high_score)

                if sound_available:
                    try:
                        pygame.mixer.music.stop()
                    except pygame.error:
                        pass

        else:
            food_rect.x -= int(food_velocity * (1.25 if ultra_event_timer>0 and score>=8 else 1.0))

        if ultra_powerup=="MAGNET" and ultra_powerup_timer>0:
            dx=player_rect.centerx-food_rect.centerx; dy=player_rect.centery-food_rect.centery
            food_rect.x += int(max(-5,min(5,dx*.035))); food_rect.y += int(max(-4,min(4,dy*.035)))

        if ultra_powerup is not None:
            ultra_powerup_x -= max(3, int(food_velocity * (1.0 if ultra_event_timer <= 0 else 1.22)))
            pr=pygame.Rect(int(ultra_powerup_x)-24,int(ultra_powerup_y)-24,48,48)
            if ultra_powerup_x < -70:
                ultra_powerup=None
                ultra_powerup_cooldown=random.randint(420,620)
            elif player_rect.colliderect(pr):
                ultra_powerups_collected += 1
                collected_powerup=ultra_powerup
                if collected_powerup=="HEART":
                    player_lives=min(player_lives+1,PLAYER_STARTING_LIVES)
                    ultra_unlock("❤️ EXTRA LIFE")
                else:
                    ultra_powerup_timer=8*FPS
                    powerup_messages={
                        "SHIELD":"🛡️ SHIELD READY",
                        "FRENZY":"🔥 2X FRENZY",
                        "MAGNET":"🧲 MAGNET ACTIVE"
                    }
                    ultra_unlock(powerup_messages.get(collected_powerup,"POWER-UP READY"))
                ultra_powerup=None; ultra_powerup_cooldown=random.randint(480,720)
                spawn_collect_particles(player_rect.centerx,player_rect.centery)

        # ---------------- COLLISION ----------------
        if game_state == "playing" and player_rect.colliderect(food_rect):

            food_center = food_rect.center

            ultra_food_collected += 1
            ultra_combo += 1; ultra_combo_timer=90; ultra_best_combo=max(ultra_best_combo,ultra_combo)
            score_gain=2 if ultra_powerup=="FRENZY" and ultra_powerup_timer>0 else 1
            score += score_gain
            # No frequent score-based notifications.
            # Combo is shown only while a real streak is active.
            spawn_score_popup(food_center[0], food_center[1] - 20)

            spawn_collect_particles(
                food_center[0],
                food_center[1]
            )

            if sound_available:
                try:
                    food_sound.play()
                except pygame.error:
                    pass

            old_difficulty = difficulty_label

            difficulty_label = get_difficulty_label(score)
            difficulty_bonus = get_difficulty_bonus(score)

            food_velocity = min(
                FOOD_MAX_VELOCITY,
                FOOD_STARTING_VELOCITY
                + (score * FOOD_ACCELERATION)
                + difficulty_bonus
            )

            if difficulty_label != old_difficulty:
                difficulty_flash = 55
                last_difficulty = difficulty_label

            check_high_score()
            reset_food()

            # WIN CONDITION.
            if score >= WIN_SCORE:
                score = WIN_SCORE
                ultra_unlock("JUNGLE MASTER")
                game_state = "won"

                if is_new_high_score:
                    save_high_score(high_score)

                if sound_available:
                    try:
                        pygame.mixer.music.stop()
                    except pygame.error:
                        pass


    # ---------------- VISUAL EFFECT TIMERS ----------------
    if cinematic_transition_frames <= 0:
        update_particles()
        update_score_popups()

    ultra_update()

    if collect_flash > 0:
        collect_flash -= 1

    if difficulty_flash > 0:
        difficulty_flash -= 1

    if screen_shake > 0:
        screen_shake -= 1

    # ---------------- DRAW ----------------
    draw_game()

    pygame.display.update()
    clock.tick(FPS)


# ---------------- SAVE HIGH SCORE ----------------
if is_new_high_score:
    save_high_score(high_score)

pygame.quit()