'''''''''
# ASTEROIDS
#   A game for Rapsberry Pi PICO/PICO W with Pico Display (PIMORONI)
#   Copyright 2023, Shunsuke Ohira
'''''''''

import time
from pimoroni import Button
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY, PEN_P4

import machine, _thread
import random

# We're only using a few colours so we can use a 4 bit/16 colour palette and save RAM!
display = PicoGraphics(display=DISPLAY_PICO_DISPLAY, pen_type=PEN_P4, rotate=0)

WIDTH, HEIGHT = display.get_bounds()
TITLE_HEIGHT = 20

display.set_backlight(0.5)
display.set_font("bitmap8")

button_a = Button(12)
button_b = Button(13)
button_x = Button(14)
button_y = Button(15)

WHITE = display.create_pen(255, 255, 255)
BLACK = display.create_pen(0, 0, 0)
CYAN = display.create_pen(0, 255, 255)
MAGENTA = display.create_pen(255, 0, 255)
YELLOW = display.create_pen(255, 255, 0)
GREEN = display.create_pen(0, 255, 0)
RED = display.create_pen(255, 0, 0)
GARNET = display.create_pen(255, 64, 64)
BLUE = display.create_pen(80, 128, 255)

FINAL_STAGE = 9
SHIPS_INIT = 3
MISSILE_RADIUS_NORMAL = 2
MISSILE_RADIUS_POWERED = 15
MISSILE_SPEED = 5
MISSILE_LENGTH = 10
MISSILE_UPGRADE_COUNT = 5
MISSILE_NORMAL = 0
MISSILE_POWERED = 1
MISSILE_EXPLODE = 2

STAGE_ENEMIES = [50,100,150,200]
ENEMY_RADIUS = 5
ENEMY_SPEED = 1
ENEMY_NORMAL = 0
ENEMY_UPGRADE_MISSILE = 1
ENEMY_ADD_SHIP = 2

'''
# Multi-core control class
#    __init__() or __init__(True) starts multi-core.
#    __init__(False) does not start multi-core, call start_multi_core() to start it.
#    start_multi_core() starts multi-core if it sleeps.
#    multi_core_task_loop() is task loop, this is an internal function so NEVER CALL THIS.
#    get_status() returns current status of multi-core.
#    worker_set() sets both a worker function and its arguments as a tuple.
#    worker_start() starts the function set by worker_set().
#    worker_stop() stops the function working.
'''
class Multi_core_class:
    def __init__(self, turn_on = True):
        self.turned_on = False
        self.worker_name = ""
        self.worker_func = None
        self.worker_args = ()
        self.worker_run = False
        self.func_run = False
        
        if turn_on:
            self.start_multi_core()

    '''
    # Start multi-core process (evaluate_candidates_multi_core)
    '''
    def start_multi_core(self):
        if not self.turned_on:
            try:
                res_thread = _thread.start_new_thread(self.multi_core_task_loop, ())
                print("START MULTI-CORE.")
            except Exception as e:
                Board_class.bg_wakeup = False
                print("COULD NOT START MULTI-CORE:", e)
                return False
        else:
            print("ALREADY STARTED MULTI-CORE.")

        self.turned_on = True
        return True

    '''
    # Task loop for the multi-core.
    # NEVER CALL THIS METHOD.  start_multi_core automatically call this method.
    '''
    def multi_core_task_loop(self):
        while True:
            if self.worker_run:
                self.func_run = True
                self.worker_func(*self.worker_args)    # Extends the arguments tuple
                self.func_run = False

    '''
    # Get multi-core status
    #   RETURN["core1_on"      ]: bool  : CORE1 is working or not
    #   RETURN["worker_name"   ]: string: Worker name
    #   RETURN["worker_started"]: bool  : Worker has been started or not
    #   RETURN["task_working"  ]: bool  : Worker function is under working or not
    '''
    def get_status(self):
        return {"core1_on": self.turned_on, "worker_name": self.worker_name, "worker_started": self.worker_run, "task_working": self.func_run}

    '''
    # Set worker function and its arguments as a tuple
    '''
    def worker_set(self, name, func, args):
        # Wait for current working function if it exists
        run = False
        if self.worker_run:
            run = True
            self.worker_stop()

        # Wait for current working function if it exists
        while self.func_run:
            time.sleep(0.05)

        # Change function and arguments
        self.worker_name = name
        self.worker_func = func
        self.worker_args = args
        
        # Re-start function
        if run:
            self.worker_start()

    '''
    # Start worker (set start-flag only, actual start is up to multi_core_task_loop())
    '''
    def worker_start(self):
        if not self.worker_func is None:
            self.worker_run = True
        else:
            self.worker_run = False

    '''
    # Stop worker (set stop-flag only, actual stop is up to multi_core_task_loop())
    '''
    def worker_stop(self):
        self.worker_run = False

########### END OF Multi_core_class ###########

'''
# Game stage class
'''
class Game_stage_class:
    def __init__(self, battle_ship):
        self.battle_ship = battle_ship
        self.str_prev = ""
        self.stars = []
        for i in list(range(20)):
            self.stars.append([random.randint(1, WIDTH), random.randint(TITLE_HEIGHT, HEIGHT), random.randint(1, 3)])

    # Clear the screen
    def clear(self, with_update = False):
        display.set_pen(BLACK)
        display.clear()
        if with_update:
            display.update()

    # Draw the game stage
    def draw(self):
        # Erase the previous text
        if self.str_prev != "":
            display.set_pen(BLACK)
            # str, x, y, word-wrapp pixels, scale (, angle, spacing, fixed-space)
            display.text(self.str_prev, 0, 0, 240, 2)
            
        # Move stars and redraw them
        for star in self.stars:
            display.set_pen(BLACK)
            display.pixel(star[0], star[1])
            star[0] = (star[0] - star[2]) % WIDTH        
            display.set_pen(WHITE)
            display.pixel(star[0], star[1])

        # Draw new text
        display.set_pen(WHITE)
        # str, x, y, word-wrapp pixels, scale (, angle, spacing, fixed-space)
        self.str_prev = "STAGE " + (str(self.battle_ship.stage) if self.battle_ship.stage <= FINAL_STAGE else "CL") + "  LEFT=" + str(self.battle_ship.ships) + "  SC=" + str(self.battle_ship.score)
        display.text(self.str_prev, 0, 0, 240, 2)

########### END OF Game_stage_class ###########


'''
# Object management class
'''
class Object_class:
    def __init__(self, speed = 1, radius = 10):
        self.display = False
        self.disappear = False
        self.speed = speed
        self.x = 0
        self.y = 0
        self.r = radius

    # Show the object, only set the flag
    def show(self, flag = True):
        self.display = flag

    # Set disappear flag (erase this in next drawing turn)
    def set_disappear(self, flag = True):
        self.disappear = flag
        
    # Set battle ship speed
    def set_speed(self, spd = 0):
        if spd > 0:
            self.speed = spd
        return self.speed

    # Move the ship relatively
    def move_rel(self, dx, dy):
        dx *= self.speed
        dy *= self.speed
        self.x += dx
        self.y += dy
        if self.x < self.r:
            self.x = self.r
        elif self.x > WIDTH - self.r:
            self.x = WIDTH - self.r

        if self.y < TITLE_HEIGHT + self.r:
            self.y = TITLE_HEIGHT + self.r
        elif self.y > HEIGHT - self.r:
            self.y = HEIGHT - self.r

    # Move the ship to absolute coordinates
    def move_abs(self, px, py):
        self.x = px
        self.y = py
        if self.x < self.r:
            self.x = self.r
        elif self.x > WIDTH - self.r:
            self.x = WIDTH - self.r

        if self.y < TITLE_HEIGHT + self.r:
            self.y = TITLE_HEIGHT + self.r
        elif self.y > HEIGHT - self.r:
            self.y = HEIGHT - self.r


'''
# An enemy space ship control class
'''
class An_Enemy_ship_class(Object_class):
    # Probabilities generating an enemy models, the probability values must be a prime number
    model_probability = [{"upgMissile": 37, "addShip": 47}, {"upgMissile": 29, "addShip": 37}, {"upgMissile": 23, "addShip": 29}, {"upgMissile": 17, "addShip": 23}]
    model_attr = [   # [color, speed_up, score, decrement score when miss this]
                    [RED   , 0,   5,  3],    # ENEMY_NORMAL
                    [GREEN , 1,  50, 25],    # ENEMY_UPGRADE_MISSILE
                    [YELLOW, 2, 100, 50]     # ENEMY_ADD_SHIP
        ]

    def __init__(self):
        super().__init__(speed = ENEMY_SPEED, radius = ENEMY_RADIUS)
        self.warp_timer = random.randint(1, 10)
        self.model = ENEMY_NORMAL
        self.set_model()
        self.move_dir_change = random.randint(1,20)
        self.move_dir = (-random.randint(1, 3), random.randint(-2, 2))

    # Set disappear flag (erase this in next drawing turn)
    def set_disappear(self, flag = True):
        super().set_disappear(flag)
        if flag:
            self.warp_timer = random.randint(1, 10)

    # Decides a model of enemy
    def set_model(self, md = 0):
        m = random.randint(0,99)
        if m % self.model_probability[md]["addShip"] == 0:
            self.model = ENEMY_ADD_SHIP
        elif m % self.model_probability[md]["upgMissile"] == 0:
            self.model = ENEMY_UPGRADE_MISSILE
        else:
            self.model = ENEMY_NORMAL

        self.set_speed(An_Enemy_ship_class.model_attr[self.model][1] + ENEMY_SPEED)

    # Get score
    def get_score(self):
        return An_Enemy_ship_class.model_attr[self.model][2]

    # Get score
    def get_dec_score(self):
        return An_Enemy_ship_class.model_attr[self.model][3]

    # Let an enemy warp-out
    def warp_out(self, md):
        if self.display == False:
            self.set_disappear(False)
            self.warp_timer -= 1
            if self.warp_timer <= 0:
                self.set_model(md)
                self.move_abs(WIDTH - self.r - random.randint(0, 30), random.randint(TITLE_HEIGHT + self.r, HEIGHT - self.r))
                self.show()
                self.warp_timer = random.randint(1, 10)
                return True
        return False

    # Draw an enemy object
    def draw(self):
        if self.display:
            # Move and redraw the enemy ship
            display.set_pen(BLACK)
            if self.model == ENEMY_NORMAL:
                display.circle(self.x, self.y, self.r)
            else:
                display.triangle(self.x-self.r, self.y, self.x+self.r, self.y-self.r, self.x+self.r, self.y+self.r)

            # Erase
            if self.disappear:
                self.show(False)
                self.set_disappear(False)
                return
            
            # Move
            self.move_dir_change -= 1
            if self.move_dir_change == 0:
                self.move_rel(self.move_dir[0], self.move_dir[1])
                self.move_dir_change = random.randint(1,20)
                self.move_dir = (self.move_dir[0], random.randint(-2, 2))
            else:
                self.move_rel(self.move_dir[0], self.move_dir[1])

            # Redraw
            if self.x <= self.r:
                self.set_disappear()
            else:
                display.set_pen(An_Enemy_ship_class.model_attr[self.model][0])
                if self.model == ENEMY_NORMAL:
                    display.circle(self.x, self.y, self.r)
                else:
                    display.triangle(self.x-self.r, self.y, self.x+self.r, self.y-self.r, self.x+self.r, self.y+self.r)

########### END OF Enemy_ship_class ###########


'''
# Enemy space ships control class
'''
class Enemy_ships_class:
    def __init__(self):
        self.model = 0
        self.generated = 0
        self.generate()
        self.enemies = []
        for i in list(range(5)):
            enemy = An_Enemy_ship_class()
            self.enemies.append(enemy)

    def set_model(self, md = None):
        if not md is None:
            self.model = md
        return self.model

    def generate(self, dn = 0):
        if dn == 0:
            self.generated = 0
        else:
            self.generated += dn
        return self.generated

    def draw(self):
        for enemy in self.enemies:
            if self.generated <= STAGE_ENEMIES[self.model]:
                if enemy.warp_out(self.model):
                    self.generate(1)
            enemy.draw()

########### END OF Enemy_ship_class ###########


'''
# Missile control class
'''
class Missile_class(Object_class):
    def __init__(self):
        super().__init__(speed = MISSILE_SPEED, radius = MISSILE_RADIUS_NORMAL)
        self.missile_grade = MISSILE_NORMAL

    # Let a missile fire
    def fire(self, px, py, grade = 0, speedup = 0):
        if self.display == False:
            self.set_disappear(False)
            self.r = MISSILE_RADIUS_NORMAL
            self.move_abs(px, py)
            self.speed = MISSILE_SPEED + speedup
            self.missile_grade = grade
            self.show()

    # Draw the missile
    def draw(self):
        if self.display:
            # Move and redraw the enemy ship
            display.set_pen(BLACK)
            display.circle(self.x, self.y, self.r)
            display.pixel_span(self.x, self.y, MISSILE_LENGTH)
            if self.disappear:
                self.show(False)
                self.set_disappear(False)
                return
            
            self.move_rel(0 if self.missile_grade == MISSILE_EXPLODE else self.speed, 0)
            if self.x >= WIDTH - self.r:
                self.set_disappear()
            else:
                display.set_pen(CYAN if self.missile_grade == MISSILE_NORMAL else MAGENTA)
                display.circle(self.x, self.y, self.r)
                display.pixel_span(self.x, self.y, MISSILE_LENGTH)

########### END OF Enemy_ship_class ###########


'''
# Space battle ship control class
'''
class Battle_ship_class(Object_class):
    def __init__(self, enemies):
        super().__init__(speed = 2, radius = 10)
        self.enemies = enemies
        
        self.ship_destroyed = False
        self.go_to_next_stage = False
        self.stage = 1
        self.score = 0
        self.score_max = 0
        self.ships = SHIPS_INIT
        self.missile_upgrade = 0

        self.x = 10
        self.y = int(HEIGHT / 2)
        self.colors = [(BLACK,BLACK,BLACK,BLACK), (YELLOW,GREEN,RED,MAGENTA), (BLUE,YELLOW,RED,MAGENTA), (GREEN,YELLOW,RED,MAGENTA)]

        # Data to erase previous ship image
        self.x_prev = -1
        self.y_prev = -1
        self.r_prev = 0
        self.u_prev = 0
        
        # Missiles
        self.missiles = []
        for i in list(range(3)):
            missile = Missile_class()
            self.missiles.append(missile)

    # Restart the game
    def restart(self, new_stage = 1):
        # Set the enemy model
        self.enemies.set_model(int((new_stage - 1) / 3))

        if self.ships <= 0 or self.stage > FINAL_STAGE:
            # Update the max score
            if self.score > self.score_max:
                self.score_max = self.score

            # Initialize the battle ship
            self.ship_destroyed = False
            self.go_to_next_stage = False
            self.missile_upgrade = 0

            self.stage = new_stage
            if new_stage == 1:
                self.score = 0
                self.ships = SHIPS_INIT

            self.set_disappear(False)
            self.show()

            # Initialize the missiles
            for missile in self.missiles:
                missile.display = False
                missile.set_disappear()

            # Initialize the enemies
            self.enemies.generate()
            for enemy in self.enemies.enemies:
                enemy.display = False
                enemy.set_disappear()

            # Clear the screen
            display.set_pen(BLACK)
            display.clear()
            return True

        return False

    # Fire a missile
    def fire(self):
        if self.display:
            for missile in self.missiles:
                if not missile.display:
                    if self.missile_upgrade == 0:
                        missile.fire(self.x + self.r, self.y, MISSILE_NORMAL)
                    else:
                        missile.fire(self.x + self.r, self.y, MISSILE_POWERED)
                        self.missile_upgrade -= 1

    # Check collisions
    #   Return True if game is over.
    def check_collisions(self):
        enemies_num = 0
        for enemy in self.enemies.enemies:
            # Miss an enemy, decement the score
            if enemy.disappear:
                if enemy.x <= enemy.r:
                    self.score -= enemy.get_dec_score()
                    if self.score < 0:
                        self.score = 0

            # An enemy alive
            elif enemy.display:
                # Speed up
                spd = enemy.set_speed(-1)
                if self.stage > 1 and spd == ENEMY_SPEED:
                    enemy.set_speed(ENEMY_SPEED + int(self.stage / 3))

                # Collision of an enemy and missiles
                enemies_num += 1
                for missile in self.missiles:
                    if missile.display:
                        # A missile collides with the battle ship
                        mx = missile.x + MISSILE_LENGTH
                        rsqr = (enemy.r + missile.r) * (enemy.r + missile.r)
                        dsqr = (enemy.x - mx) * (enemy.x - mx) + (enemy.y - missile.y) * (enemy.x - missile.y)
                        if dsqr < rsqr:
                            self.score += enemy.get_score()

                            # Add a ship up to the maximum
                            if enemy.model == ENEMY_ADD_SHIP:
                                if self.ships < SHIPS_INIT:
                                    self.ships += 1
                                    
                            # Upgrade missile for a while
                            elif enemy.model == ENEMY_UPGRADE_MISSILE:
                                self.missile_upgrade += MISSILE_UPGRADE_COUNT

                            enemy.set_disappear()
                            
                            # Change to powerd missile
                            if missile.missile_grade == MISSILE_POWERED:
                                missile.r = MISSILE_RADIUS_POWERED
                                missile.missile_grade = MISSILE_EXPLODE
                            # Exploded powered missole
                            elif missile.missile_grade == MISSILE_EXPLODE:
                                missile.missile_grade = MISSILE_NORMAL
                            # Normal missile
                            else:
                                missile.set_disappear()
                                
                            break
                        
                if enemy.disappear:
                    continue

                # An enemy collides with the battle ship
                rsqr = (enemy.r + self.r) * (enemy.r + self.r)
                dsqr = (enemy.x - self.x) * (enemy.x - self.x) + (enemy.y - self.y) * (enemy.y - self.y)
                if dsqr < rsqr:
                    self.ships -= 1
                    if self.ships > 0:
                        self.ship_destroyed = True
                        for emy in self.enemies.enemies:
                            emy.set_disappear()
                            emy.display = False

                        return False

                    # Game over
                    self.set_disappear()
                    self.ships = 0
                    for missile in self.missiles:
                        if missile.display:
                            missile.set_disappear()
                    return True

        # No enemy, stage clear
        if self.enemies.generated >= STAGE_ENEMIES[self.enemies.set_model()] and enemies_num == 0 and not self.ship_destroyed:
            self.go_to_next_stage = True
        
        return False

    # Draw the battle ship
    def draw(self):
        def draw_ship(x, y, r, u, colors):
            if u > 0:
                display.set_pen(colors[3])
                display.circle(x, y, r)
                display.circle(x, y, r-1)
            display.set_pen(colors[0])
            display.triangle(x+r, y, x-r+2, y-r, x-r+2, y+r)
            display.set_pen(colors[2])
            display.rectangle(x-r, y-r+4, 4, r+r-8)
            display.set_pen(colors[1])
            display.rectangle(x-r+2, y-r+2, r+2, 3)
            display.rectangle(x-r+2, y+r-4, r+2, 3)

        # Redraw the battle ship
        if self.display:
            # Move and draw missiles
            for missile in self.missiles:
                missile.draw()

            # Erase the previous object
            if self.r_prev > 0:
                draw_ship(self.x_prev, self.y_prev, self.r_prev, self.u_prev, self.colors[0])

            if self.disappear:
                self.show(False)
                return

            # Draw new object and save to the variables for the previous data
            draw_ship(self.x, self.y, self.r, self.missile_upgrade, self.colors[self.ships])
            self.x_prev = self.x
            self.y_prev = self.y
            self.r_prev = self.r
            self.u_prev = self.missile_upgrade

########### END OF Multi_core_class ###########

'''
# Draw all game objects, works in the multi-core process
'''
def draw_display(core1, game_stage, battle_ship, enemy_ships):
#    st = core1.get_status()
#    print(st["worker_name"] + " DRAW")

    # In play
    if battle_ship.ships > 0:
        # Stage clear
        if battle_ship.go_to_next_stage:
            # Clear all stages, game end
            if battle_ship.stage >= FINAL_STAGE:
                battle_ship.stage = FINAL_STAGE + 1
                game_stage.draw()
                enemy_ships.draw()
                display.set_pen(GREEN)
                display.text("GAME CLEAR", 0, 20, 240, 5)
                if battle_ship.score > battle_ship.score_max:
                    display.set_pen(MAGENTA)
                    display.text("HIGH SCORE!!", 22, 67, 240, 4)
                else:
                    display.set_pen(CYAN)
                    display.text("HIGH-SC=" + str(battle_ship.score_max), 15, 73, 240, 3)
                display.set_pen(GREEN)
                display.text("X: REPLAY", 65, 111, 240, 3)

            # Next stage
            else:
                display.set_pen(YELLOW)
                for i in [3,2,1]:
                    display.set_pen(CYAN)
                    msg = "STAGE CLR" + "." * i
                    display.text(msg, 12, 50, 240, 4)
                    display.update()
                    time.sleep(1)
                    display.set_pen(BLACK)
                    display.text(msg, 12, 50, 240, 4)

                battle_ship.stage += 1
                battle_ship.go_to_next_stage = False
                enemy_ships.generate()
                battle_ship.restart(battle_ship.stage)
                game_stage.clear()

        # The battle ship has been destroyed, then clear this stage
        elif battle_ship.ship_destroyed:
            display.set_pen(YELLOW)
            for i in [3,2,1]:
                display.set_pen(YELLOW)
                msg = "DESTROYED" + "." * i
                display.text(msg, 12, 50, 240, 4)
                display.update()
                time.sleep(1)
                display.set_pen(BLACK)
                display.text(msg, 12, 50, 240, 4)

            battle_ship.ship_destroyed = False
            game_stage.clear()

        # Check collisions of objects in the game screen
        battle_ship.check_collisions()

        # Move objects and redraw the game screen
        game_stage.draw()
        enemy_ships.draw()
        battle_ship.draw()

    # Game over
    elif battle_ship.ships == 0:
        game_stage.draw()
        enemy_ships.draw()
        display.set_pen(YELLOW)
        display.text("GAME OVER", 15, 20, 240, 5)
        if battle_ship.score > battle_ship.score_max:
            display.set_pen(MAGENTA)
            display.text("HIGH SCORE!!", 22, 67, 240, 4)
        else:
            display.set_pen(CYAN)
            display.text("HIGH-SC=" + str(battle_ship.score_max), 15, 73, 240, 3)
        display.set_pen(GREEN)
        display.text("X: REPLAY", 65, 111, 240, 3)

    # Start up
    else:
        game_stage.draw()
        display.set_pen(BLACK)
        display.rectangle(0, 0, WIDTH, TITLE_HEIGHT)
        display.set_pen(YELLOW)
        display.text("--ASTEROIDS--", 3, 0, 240, 4)
        display.set_pen(RED)
        display.text("A: MOVE UP", 15, 30, 240, 3)
        display.text("B: MOVE DOWN", 15, 57, 240, 3)
        display.text("Y: FIRE A MISSILE", 15, 84, 240, 3)
        display.set_pen(GREEN)
        display.text("X: PLAY", 15, 111, 240, 3)

    display.update()
    time.sleep(0.01)


'''
### MAIN ###
'''
if __name__=='__main__':
    # CPU clock 240MHz
#    machine.freq(133000000)
    machine.freq(240000000)

    # Prepare game
    enemy_ships = Enemy_ships_class()

    battle_ship = Battle_ship_class(enemy_ships)
    battle_ship.set_speed(3)

    game_stage = Game_stage_class(battle_ship)
    game_stage.clear(True)
    
#    battle_ship.show()
    battle_ship.ships = -1

    # Prepare multi-core
    multi_core = Multi_core_class()
    if multi_core.get_status()["core1_on"]:
        print("CORE1 TURNED ON: ", multi_core.get_status())
        multi_core.worker_set("GAME_DISPLAY", draw_display, (multi_core, game_stage, battle_ship, enemy_ships))
        multi_core.worker_start()
    else:
        print("MUTI-CORE TASK DOES NOT WORK.")

    # Main-core event loop
    while True:
        # Move up the battle ship
        if button_a.read():                                   # if a button press is detected then...
            battle_ship.move_rel(0, -1)

        # Move down the battle ship
        if button_b.read():
            battle_ship.move_rel(0,  1)
#            print("MOVE DOWN")

        # Restart the game
        if button_x.read():
            if battle_ship.ships <= 0 or battle_ship.stage > FINAL_STAGE:
                game_stage.clear(True)
                battle_ship.restart()
#            print("RESTART")

        # Fire a missile
        if button_y.read():
            battle_ship.fire()
#            print("FIRE A MISSILE")

        time.sleep(0.02)
