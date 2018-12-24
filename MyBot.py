#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
from typing import List, Any

from hlt import Game

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction

# Import position class for navigation
from hlt.positionals import Position

# This library allows you to generate random numbers.
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

import itertools

from itertools import groupby

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = Game()

# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.


class Admiral:

    def __init__(self):
        self.command_queue = None
        self.ships = None
        self.moves = None
        self.ship_next_position = None
        self.ship_next_direction = None
        self.locations_collision_imminent = None
        self.ships_collision_imminent = None

    def command_safe_moves(self, ships, moves):
        self.command_queue = []
        self.ships = ships
        self.moves = moves
        self.ship_next_position = {}
        self.ship_next_direction = {}
        self.locations_collision_imminent = []
        self.ships_collision_imminent = []

        for ship, move in zip(self.ships, self.moves):
            self.set_position_occupied_next_turn(ship, move)
            self.set_direction_next_turn(ship, move)

        if self.is_collision_imminent():
            self.update_locations_collision_imminent()
            self.reroute_ships_to_avoid_collisions()

        for ship in self.ships:
            self.command_queue.append(ship.move(self.ship_next_direction[ship.id]))
        return self.command_queue

    def get_positions_occupied_next_turn(self):
        return list(self.ship_next_position.values())

    def set_position_occupied_next_turn(self, ship, move):
        self.ship_next_position[ship.id] = ship.position.directional_offset(move)

    def set_direction_next_turn(self, ship, move):
        self.ship_next_direction[ship.id] = move

    def is_collision_imminent(self):
        next_locations = list(self.ship_next_position.values())
        while len(next_locations) > 1:
            if next_locations.pop() in next_locations:
                return True
        return False

    def update_locations_collision_imminent(self):
        self.locations_collision_imminent = []
        self.ships_collision_imminent = []
        next_locations = list(self.ship_next_position.values())
        ships = list(self.ship_next_position.keys())

        # look for dupes in the next_locations. Dupes are collisions
        # Add ships and locations of dupes to collision imminent lists
        # Update moves assuming they stay still as they are about to collide
        while len(next_locations) > 1:
            test_location = next_locations.pop()
            if test_location in next_locations and test_location not in self.locations_collision_imminent:
                self.locations_collision_imminent.append(test_location)
                for ship in self.ships:
                    if self.ship_next_position[ship.id] == test_location:
                        self.ships_collision_imminent.append(ship)
        # for ships about to collide, set their positions and directions for next round
        # as though they will not move
        for ship in self.ships_collision_imminent:
            self.set_direction_next_turn(ship, Direction.Still)
            self.set_position_occupied_next_turn(ship, Direction.Still)

    def reroute_ships_to_avoid_collisions(self):
        for ship, move in zip(self.ships, self.moves):
            self.set_direction_next_turn(ship, Direction.Still)
            if self.ship_next_position[ship.id] in self.locations_collision_imminent:
                if move == Direction.Still:
                    break

                elif ship_status[ship.id] == 'harvesting':
                    self.harvesting_go_safe_position(ship)

                elif ship_status[ship.id] == 'returning':
                    self.returning_go_safe_position(ship, me.shipyard.position)

                else:
                    break

    def harvesting_go_safe_position(self, ship, try_directions=None):
        if try_directions is None:
            try_directions = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]
        if len(try_directions) == 0 or get_halite_in_direction(Direction.Still) >= HARVEST_HALITE_LOWER_LIMIT:
            return Direction.Still
        go_direction = find_safe_direction_most_halite(try_directions)
        if ship.position.directional_offset(go_direction) in self.get_positions_occupied_next_turn():
            try_directions.remove(go_direction)
            self.harvesting_go_safe_position(ship, try_directions)
        else:
            self.ship_next_direction(ship, go_direction)
            self.ship_next_position(ship, go_direction)

    def returning_go_safe_position(self, ship, destination, try_directions=None):
        if try_directions is None:
            try_directions = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]
            go_direction = smart_navigate(ship, destination, try_directions)
            if ship.position.directional_offset(go_direction) in self.get_positions_occupied_next_turn():
                try_directions.remove(go_direction)
                self.returning_go_safe_position(ship, try_directions)
            else:
                self.ship_next_direction(ship, go_direction)
                self.ship_next_position(ship, go_direction)


admiral = Admiral()

game.ready("LikeABotOutOfHalite")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """


def get_total_halite(game_map):
    game_height = game_map.height
    game_width = game_map.width
    total_halite = 0
    for x_pos in range(game_width):
        for y_pos in range(game_height):
            position = Position(x_pos, y_pos)
            total_halite += game_map[(position)].halite_amount
    return total_halite


total_halite = get_total_halite(game.game_map)
number_of_players = len(list(game.players.keys()))
REVENUE_EXPECTATION = 8000
SHIP_UPPER_LIMIT = total_halite / REVENUE_EXPECTATION
SHIP_LOWER_LIMIT = 5
SPAWN_TURN_LIMIT = 250
NUMBER_OF_TURNS_SUPPRESS_ALL_SPAWNS = 20
HARVEST_HALITE_LOWER_LIMIT = 0
ROLLUP_TURN_BUFFER = 7

# A command queue holds all the commands you will run this turn. You build this list up and submit it at the
#   end of the turn.
command_queue = []
ship_status = {}
while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    moves = []

    for ship in me.get_ships():

        move = determine_move(ship)
        moves.append(move)

    command_queue = admiral.command_safe_moves(list(me.get_ships()), moves)

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    my_number_ships = len(me.get_ships())
    if my_number_ships < SHIP_UPPER_LIMIT \
    and (game.turn_number <= SPAWN_TURN_LIMIT or my_number_ships < SHIP_LOWER_LIMIT) \
    and me.halite_amount >= constants.SHIP_COST \
    and not game_map[me.shipyard].is_occupied\
    and game.turn_number < constants.MAX_TURNS - NUMBER_OF_TURNS_SUPPRESS_ALL_SPAWNS:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)


    def determine_move(ship):

        set_status_ship_at_shipyard(ship)

        if ship_status[ship.id] == 'harvesting':
            move = get_move_harvesting(ship)

        if ship.is_full or ship_status[ship.id] == 'returning':
            move = get_move_returning_ship(ship)

        return move


    def set_status_ship_at_shipyard(ship):
        if ship.position == me.shipyard.position or ship.id not in ship_status:
            ship_status[ship.id] = 'harvesting'

    def get_move_harvesting(ship):
        ship_status[ship.id] = 'harvesting'
        move = find_safe_direction_most_halite()
        return move


    def get_move_returning_ship(ship):
        ship_status[ship.id] = 'returning'
        return_move = smart_navigate(ship, me.shipyard.position)
        return return_move

    def find_safe_direction_most_halite(directions=None):
        if directions is None:
            directions = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]

        if get_halite_in_direction(Direction.Still) > HARVEST_HALITE_LOWER_LIMIT:
            return Direction.Still

        max_halite_found = 0
        total_halite_found = 0
        best_direction = random.choice(directions)
        for direction in directions:
            test_halite_amount = get_halite_in_direction(direction)
            total_halite_found += test_halite_amount
            if test_halite_amount > max_halite_found:
                max_halite_found = test_halite_amount
                best_direction = direction
        if max_halite_found >= HARVEST_HALITE_LOWER_LIMIT:
            return best_direction
        else:
            return random.choice(directions)

    def get_halite_in_direction(direction):
        test_location = ship.position.directional_offset(direction)
        test_halite_amount = game_map[test_location].halite_amount
        return test_halite_amount

    def smart_navigate(ship, destination, directions=None):
        # safe_directions = find_safe_directions(ship)
        # if len(safe_directions) == 0:
        #     return Direction.Still
        if directions is None:
            directions = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]
        min_distance = 1000
        best_direction = random.choice(directions)
        for direction in directions:
            test_location = ship.position.directional_offset(direction)
            distance = game_map.calculate_distance(test_location, destination)
            if distance < min_distance:
                min_distance = distance
                best_direction = direction
        return best_direction
