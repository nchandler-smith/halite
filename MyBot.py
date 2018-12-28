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

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
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


def assign_ship_status(ship):
    current_ship_position = ship.position
    if ship.id not in ship_status.keys():
        ship_status[ship.id] = 'explore'
    if ship_status[ship.id] == 'returning':
        if current_ship_position == me.shipyard.position:
            ship_status[ship.id] = 'explore'
    elif game_map[current_ship_position].halite_amount > 0 and not ship.is_full:
        ship_status[ship.id] = 'harvest'
    elif ship.is_full:
        ship_status[ship.id] = 'returning'
    elif ship_status[ship.id] == 'explore_fringe':
        pass
    else:
        ship_status[ship.id] = 'explore'


def handle_ships_staying_to_harvest(ship):
    if ship_status[ship.id] == 'harvest':
        fleet_move_chart[ship.id] = Direction.Still
        fleet_positions_next_turn.append(ship.position.directional_offset(Direction.Still))


def safe_navigate(ship, destination):
    directions = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]
    min_distance = 1000
    best_direction = Direction.Still
    for direction in directions:
        test_location = ship.position.directional_offset(direction)
        distance = game_map.calculate_distance(test_location, destination)
        if distance < min_distance and test_location not in fleet_positions_next_turn:
            min_distance = distance
            best_direction = direction
    return best_direction


def evaluate_halite_in_direciton(position):
    total_halite_found = 0
    for i in range(-3, 3):
        for j in range(7):
            scan_position = Position(i, j)
            total_halite_found += game_map[position + scan_position].halite_amount
    return total_halite_found


def get_direction_most_halite(ship):
    directions = [Direction.North, Direction.South, Direction.East, Direction.West]
    max_halite_found = -1
    best_direction = Direction.Still
    for test_direction in directions:
        test_location = ship.position.directional_offset(test_direction)
        halite_at_test_location = evaluate_halite_in_direciton(test_location)
        if halite_at_test_location > max_halite_found and test_location not in fleet_positions_next_turn:
            best_direction = test_direction
            max_halite_found = halite_at_test_location
    explore_fringe(ship, best_direction)
    return best_direction


def explore_fringe(ship, direction):
    root_position = ship.position.directional_offset(direction)
    box_size = 7
    for i in range(0, box_size//2):
        new_position_1 = root_position + Position(i, 0)
        if new_position_1 not in fleet_positions_next_turn:
            ship_destination[ship.id] = new_position_1
            ship_status[ship.id] = 'explore_fringe'
            return new_position_1
        new_position_2 = root_position + Position(-1*i, 0)
        if new_position_2 not in fleet_positions_next_turn:
            ship_destination[ship.id] = new_position_2
            ship_status[ship.id] = 'explore_fringe'
            return new_position_2
    return root_position


def get_direction_to_move(ship):
    if ship_status[ship.id] != 'harvest':

        if ship_status[ship.id] == 'explore':
            go_direction = get_direction_most_halite(ship)

        elif ship_status[ship.id] == 'returning':
            go_direction = safe_navigate(ship, me.shipyard.position)

        elif ship_status[ship.id] == 'explore_fringe':
            go_direction = safe_navigate(ship, ship_destination[ship.id])

        fleet_move_chart[ship.id] = go_direction
        go_position = ship.position.directional_offset(go_direction)
        fleet_positions_next_turn.append(go_position)


map_starting_halite_total = get_total_halite(game.game_map)
REVENUE_EXPECTATION = 8000
NUMBER_OF_SHIPS_UPPER_LIMIT = map_starting_halite_total / REVENUE_EXPECTATION
NUMBER_OF_SHIPS_LOWER_LIMIT = 5
SPAWN_TURN_LIMIT = 250

ship_status = {}
ship_destination = {}
while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []
    fleet_move_chart = {}
    fleet_positions_next_turn = []

    for ship in me.get_ships():
        assign_ship_status(ship)
        handle_ships_staying_to_harvest(ship)

    for ship in me.get_ships():
        get_direction_to_move(ship)

    for ship in me.get_ships():
        command_queue.append(ship.move(fleet_move_chart[ship.id]))

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if (len(me.get_ships()) < NUMBER_OF_SHIPS_LOWER_LIMIT or game.turn_number <= SPAWN_TURN_LIMIT) \
            and len(me.get_ships()) < NUMBER_OF_SHIPS_UPPER_LIMIT \
            and me.halite_amount >= constants.SHIP_COST \
            and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
