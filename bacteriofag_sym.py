import sys
import os
import numpy as np

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"    # Do not print pygame welcome message into console (has to be set before importing pygame)
import pygame
from pygame._sdl2.video import Window

# List of colors:
# python3 -c "import pygame; print('\\n'.join([i + '\\t\\t' + str(v) for i,v in pygame.color.THECOLORS.items()]))"
def col(name):
	return pygame.color.THECOLORS[name]

def precise_collision(sprite1, sprite2):
    hitbox1 = sprite1.rect
    hitbox2 = sprite2.rect

    if hasattr(sprite1, 'colliderect'): hitbox1 = sprite1.colliderect
    if hasattr(sprite2, 'colliderect'): hitbox2 = sprite2.colliderect

    return hitbox1.colliderect(hitbox2)


# Class for compact storage of images
class Graphics:
    def __init__(self, path="Images/"):
        # Import all images and convert them to same format as display surface, with alpha channel

        self.phage = pygame.image.load(path+"Bacteriophage.png")  # Virion image
        self.phage = self.phage.convert_alpha()
        self.phage = self.colorize(self.phage, col("red"))  # Color red


    @staticmethod
    def colorize(image, color): # Recolors image
        image = image.copy()

        image.fill(color, None, pygame.BLEND_RGB_MULT)

        return image

# Parent class for bacteria and virions
class Dot(pygame.sprite.Sprite):
    def __init__(self, x, y, parent_surface, width, height, containers, rng = None):
        super().__init__()

        if not rng:
            self.rng = np.random.default_rng()
        else:
            self.rng = rng

        self.image = pygame.Surface((width, height))
        self.image = self.image.convert_alpha()

        self.pos = np.array([x, y], dtype=np.float64)
        self.rect = self.image.get_rect(center=self.pos)
        self.vel = np.asarray([0, 0], dtype=np.float64)

        self.parent_surface = parent_surface

        containers = list(containers)
        self.containers = containers
        self.add(*containers)

    def move_containers(self, containers, replace=True):
        containers = list(containers)

        if replace:
            self.containers = containers
        else:
            self.containers.extend(containers)

        self.kill()    # This merely removes sprite from all groups so it can then be re-added, don't worry
        self.add(*self.containers)

    def __fix_color(self, color):
        if 3 > len(color) > 4:
            raise ValueError("Invalid length of color array.")

        color = pygame.Color([min(255, max(0,int(component))) for component in color])

        return color

    def update(self):
        self.pos += self.vel
        x, y = self.pos

        # Periodic boundary conditions
        if x < 0:
            self.pos[0] = self.WIDTH
            x = self.WIDTH
        if x > self.WIDTH:
            self.pos[0] = 0
            x = 0
        if y < 0:
            self.pos[1] = self.HEIGHT
            y = self.HEIGHT
        if y > self.HEIGHT:
            self.pos[1] = 0
            y = 0

        self.rect.x = x
        self.rect.y = y

        # Brownian
        old_vel = self.vel.copy()

        change = self.rng.uniform(-1, 1, 2)
        change = (change[0]/np.sqrt(change[0]**2 + change[1]**2), change[1]/np.sqrt(change[0]**2 + change[1]**2))
        self.vel = change

        vel_norm = np.linalg.norm(self.vel)
        if vel_norm > 5:
            self.vel = old_vel

class Bacteria(Dot):
    def __init__(self, x, y, surface, containers, rng=None):
        super().__init__(x, y, surface, 25, 25, containers, rng)

        self.image.set_alpha(200)   # Make bacteria semi-transparent

        # Randomized shape
        R = pygame.Rect(0,0, self.rect.width, self.rect.height)
        cell_l = self.rng.integers(0, R.center[0]//2, endpoint=True)
        cell_t = self.rng.integers(0, R.center[1]//2, endpoint=True)

        max_w = min(R.width, R.right - cell_l)
        max_h = min(R.height, R.bottom - cell_t, max_w*4//3)

        cell_w = self.rng.integers(R.width*3//4, max_w, endpoint=True)
        cell_h = self.rng.integers(R.height*3//4, max_h, endpoint=True)

        self.membrane = pygame.Rect(cell_l, cell_t, cell_w, cell_h)
        self.cytoplasm = self.membrane.copy()
        self.cytoplasm.top += 3
        self.cytoplasm.left += 3
        self.cytoplasm.width -= 6
        self.cytoplasm.height -= 6

        # Special hitbox
        self.offset = np.asarray([self.membrane.center[0] - R.center[0],
                                  self.membrane.center[1] - R.center[1]],
                                 dtype=np.float64)

        self.colliderect = self.membrane.copy()
        self.colliderect.center = self.pos + self.offset

        self.__draw()

        self.deathclock = None

    def __draw(self, color=col("green")):

        if len(color) < 3: color = list(color + [255])
        dark = tuple([i*2//3 for idx, i in enumerate(color) if idx < 3] + [color[3]])
        even_darker = tuple([i*2//3 for idx, i in enumerate(dark) if idx < 3] + [dark[3]])

        self.image.fill((0,0,0,0))
        pygame.draw.ellipse(self.image, dark, self.membrane)
        pygame.draw.ellipse(self.image, color, self.cytoplasm)

    def infect(self, deathclock=30):
        self.deathclock = deathclock
        self.__draw(color=col("yellow"))

    def update(self):
        self.pos += self.vel
        x, y = self.pos
        s_x, s_y = self.parent_surface.get_size()

        # Periodic boundary conditions
        if x < 0:
            x += s_x
        if x > s_x:
            x -= s_x
        if y < 0:
            y += s_y
        if y > s_y:
            y -= s_y

        self.pos = np.asarray([x, y], dtype=np.float64)
        self.rect.center = self.pos
        self.colliderect.center = self.pos + self.offset

        # Brownian
        old_vel = self.vel.copy()

        change = self.rng.uniform(-1, 1, 2)
        change = (change[0]/np.sqrt(change[0]**2 + change[1]**2), change[1]/np.sqrt(change[0]**2 + change[1]**2))
        self.vel += change

        vel_norm = np.linalg.norm(self.vel)
        if vel_norm > 3:
            self.vel = old_vel

        if self.deathclock != None:

            if self.deathclock == 0:
                self.kill()
                return 1    # This informs main loop that virions & lysed bacteria must be spawned

            self.deathclock -= 1

class Lysed_bacteria(Dot):
    def __init__(self, x, y, surface, containers, rng=None):
        super().__init__(x, y, surface, 25, 25, containers, rng)

        # Randomized positions of cell "fragments"
        self.fragments = [self.rng.integers((2, 2), (self.rect.width-1, self.rect.height-1), size=2) for _ in range(10)]
        self.shapes = [self.rng.choice(("circle", "rectangle")) for _ in range(10)]

        self.__draw()

        self.deathclock = self.rng.integers(100, 200, endpoint=True)

    def __draw(self, color=col("yellow")):
        self.image.fill((0,0,0,0))

        for i in range(10):
            f_x, f_y = self.fragments[i]

            match self.shapes[i]:
                case "circle":
                    pygame.draw.circle(self.image,
                                        color,
                                        (f_x, f_y),
                                        2, 2)

                case "rectangle":
                    pygame.draw.rect(self.image,
                                        color,
                                        pygame.Rect(f_x-1, f_y-1, 2, 2))

    def update(self):
        if self.deathclock != None:
            if self.deathclock == 0:
                self.kill()
                return 0

            self.deathclock -= 1

class Virion(Dot):
    def __init__(self, x, y, surface, containers, graphics, rng=None):
        # Apply defaults from Dot class
        super().__init__(x, y, surface, 19, 19, containers, rng)

        # Special collision box
        self.colliderect = pygame.Rect(0, 0, 15, 15)
        self.colliderect.center = self.pos - np.asarray([2,2], dtype=np.float64)

        # Custom graphics
        self.phage = graphics.phage.copy()
        self.rotation = self.rng.choice(tuple(range(-175, 181, 15)))
        self.rotation_speed = self.rng.choice((-15, 15))
        self.__draw()

        # Add timers
        self.lifetime = 0
        self.deathclock = self.rng.integers(50, 100, endpoint=True)

    def __draw(self, color=col("red")):
        self.image.fill((0,0,0,0))
        self.image.blit(pygame.transform.rotate(self.phage, self.rotation), (0,0))

    def update(self):
        self.pos += self.vel
        x, y = self.pos
        s_x, s_y = self.parent_surface.get_size()

        # Periodic boundary conditions
        if x < 0:
            x += s_x
        if x > s_x:
            x -= s_x
        if y < 0:
            y += s_y
        if y > s_y:
            y -= s_y

        self.pos = np.asarray([x, y], dtype=np.float64)
        self.rect.center = self.pos
        self.colliderect.center = self.pos - np.asarray([2,2], dtype=np.float64)

        # Brownian
        old_vel = self.vel.copy()

        change = self.rng.uniform(-1, 1, 2)
        change = (change[0]/np.sqrt(change[0]**2 + change[1]**2), change[1]/np.sqrt(change[0]**2 + change[1]**2))
        self.vel += change

        vel_norm = np.linalg.norm(self.vel)

        # Speed limit - if pythagorean distance expressed by velocity vector is too high, revert it
        if vel_norm > 5:
            self.vel = old_vel


        # Rotation
        if self.lifetime % 5 == 0:
            self.rotation += self.rotation_speed
            self.__draw()

        if self.deathclock != None:
            if self.deathclock == 0:
                self.kill()
                return 0

            self.deathclock -= 1

        self.lifetime += 1


class Simulation:
    def __init__(self, width=1600, height=900, screen=None, sys_size=None, debug=False):

        self.debug = debug
        self.rng = np.random.default_rng()

        self.WIDTH = width	# window width
        self.HEIGHT = height	# window height

        #self.virus_lifecycles_range = (50, 100)
        #self.virions_count = (2, 6)

        # Smh there is no actually very dark blue in pygame's set, so here's some dark aqua
        self.bgcol = (5, 30, 40, 255)

        if not screen:
            self.screen = pygame.display.set_mode((width, height), flags=pygame.HIDDEN)
            pygame.display.set_caption('Symulacja rozwoju wirusa w kolonii bakteryjnej')

        else:
            self.screen = screen
            self.WIDTH, self.HEIGHT = screen.get_size()


        # Place the window in the middle of screen
        # Only necessary because subsequent calls on pygame.display.set_mode()
        # for some reason relocate the window bit lower every time.
        # And window moving every time you restart of course looks bad.
        if sys_size:
            scr_pos = ( (sys_size[0]-self.WIDTH)//2, (sys_size[1]-self.HEIGHT)//2 )
            sys_window = Window.from_display_module()
            sys_window.position = scr_pos

        self.screen.fill(self.bgcol)

        self.susceptible_container = pygame.sprite.Group()
        self.virus_container = pygame.sprite.Group()
        self.bacteria_infected_container = pygame.sprite.Group()
        self.dead_container = pygame.sprite.Group()
        self.all_container = pygame.sprite.Group()

        self.graphics = Graphics() # Load and prepare images

        self.n_susceptible = 20
        self.n_infected = 1
        #self.n_quarantined = 0
        #self.cycle_to_fate = 20
        #self.mortality_rate = 1

    def start(self):

        self.N = self.n_susceptible + self.n_infected #+ self.n_quarantined

        screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))

        for _ in range(self.n_susceptible):    # Spawn bacteria
            x = self.rng.integers(0, self.WIDTH, endpoint=True)
            y = self.rng.integers(0, self.HEIGHT, endpoint=True)

            Bacteria(x, y, screen, containers=[self.susceptible_container,
                                               self.all_container], rng=self.rng)

        '''
        for i in range(self.n_quarantined):
            x = np.random.randint(0, self.WIDTH + 1)
            y = np.random.randint(0, self.HEIGHT + 1)
            vel = [0, 0]
            guy = Dot(x, y, self.WIDTH, self.HEIGHT, color=col("green"), velocity=vel)
            self.susceptible_container.add(guy)
            self.all_container.add(guy)
        '''

        for _ in range(self.n_infected):    # Spawn virions
            x = self.rng.integers(0, self.WIDTH, endpoint=True)
            y = self.rng.integers(0, self.HEIGHT, endpoint=True)
            Virion(x, y, screen, containers=[self.virus_container,
                                             self.all_container],
                                 graphics=self.graphics, rng=self.rng)

        clock = pygame.time.Clock()

        # Main loop
        pause = False
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:    # If "X" button was clicked, end the program
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        pause = (pause + 1) %2

                    elif event.key == pygame.K_RETURN:
                        pygame.display.set_mode((self.WIDTH, self.HEIGHT), pygame.HIDDEN)
                        return screen

            if pause:
                clock.tick(10)
                continue

            for sprite in self.all_container:    # Call .update() method on all sprites
                action = sprite.update()
                if action and sprite.__class__ == Bacteria:
                    for _ in range(self.rng.integers(2,6)):  # Spawn virions & lysed bacteria
                        Virion(self.rng.integers(sprite.rect.left,
                                                 sprite.rect.right,
                                                 endpoint=True),
                               self.rng.integers(sprite.rect.top,
                                                 sprite.rect.bottom,
                                                 endpoint=True),
                               screen,
                               [self.virus_container, self.all_container],
                               graphics=self.graphics,
                               rng=self.rng)

                    Lysed_bacteria(sprite.pos[0], sprite.pos[1],
                                    screen, [self.dead_container, self.all_container],
                                    rng=self.rng)

            screen.fill(self.bgcol)        # Fill screen with background color (erases all objects)


            ## New infections

            # Find all viruses & non-immune bacteria which collided
            collision_group = pygame.sprite.groupcollide(
                self.virus_container,
                self.susceptible_container,
                False,
                True,
                precise_collision)    # removes bacteria that collided from suspectible_container

            for virus in collision_group:    # Loop over viruses that collided with anything
                bacteria = collision_group[virus][0]    # Select first bacteria that collided and infect it

                bacteria.infect()
                bacteria.move_containers([self.bacteria_infected_container,
                                          self.all_container])

                virus.kill()

            self.dead_container.draw(screen)
            self.susceptible_container.draw(screen)
            self.bacteria_infected_container.draw(screen)
            self.virus_container.draw(screen)

            if self.debug:
                for bact in self.susceptible_container:
                    pygame.draw.rect(screen, col("green"), bact.colliderect, 1)
                for bact in self.bacteria_infected_container:
                    pygame.draw.rect(screen, col("yellow"), bact.colliderect, 1)
                for virus in self.virus_container:
                    pygame.draw.rect(screen, col("red"), virus.rect, 1)

            pygame.display.flip()
            clock.tick(30)

        return screen


if __name__ == '__main__':
    debug = False
    if len(sys.argv) > 1:
        if "--debug" in sys.argv:   debug = True

    pygame.init()
    sys_screen = pygame.display.Info()
    sys_size = (sys_screen.current_w, sys_screen.current_h)

    screen = None
    while True:
        bacteriophage = Simulation(screen=screen, sys_size=sys_size, debug=debug)
        bacteriophage.n_susceptible = 200
        #bacteriophage.n_quarantined = 0
        bacteriophage.n_infected = 3
        #bacteriophage.cycle_to_fate = 150
        #bacteriophage.mortality_rate = 0.8
        #bacteriophage.virions_count = (1, 6)
        #bacteriophage.virus_lifecycles_range = (200, 250)

        screen = bacteriophage.start()
