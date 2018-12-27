#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction

# This library allows you to generate random numbers.
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("MyPythonBot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """


def position_to_tuple(position):
    return position.x, position.y


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
    else:
        ship_status[ship.id] = 'explore'


def handle_ships_staying_to_harvest(ship):
    if ship_status[ship.id] == 'harvest':
        fleet_move_chart[ship.id] = Direction.Still
        fleet_positions_next_turn[ship.id] = position_to_tuple(ship.position)


def safe_navigate(ship, destination, directions):
    min_distance = 1000
    best_direction = random.choice(directions)
    for direction in directions:
        test_location = ship.position.directional_offset(direction)
        distance = game_map.calculate_distance(test_location, destination)
        if distance < min_distance:
            min_distance = distance
            best_direction = direction
    return best_direction


def get_direction_most_halite(ship, directions):
    max_halite_found = 0
    best_direction = random.choice(directions)
    for test_direction in directions:
        test_location = ship.position.directional_offset(test_direction)
        halite_at_test_location = game_map[test_location].halite_amount
        if halite_at_test_location > max_halite_found:
            best_direction = test_direction
            max_halite_found = halite_at_test_location
    return best_direction


def get_direction_to_move(ship, allowed_directions=None):
    if ship_status[ship.id] != 'harvest':

        if allowed_directions is None:
            allowed_directions = [Direction.North, Direction.South, Direction.East, Direction.West]

        if ship_status[ship.id] == 'explore':
            test_direction = get_direction_most_halite(ship, allowed_directions)

        if ship_status[ship.id] == 'returning':
            test_direction = safe_navigate(ship, me.shipyard.position, allowed_directions)

        test_position = ship.position.directional_offset(test_direction)
        if position_to_tuple(test_position) in fleet_positions_next_turn.values():
            allowed_directions.remove(test_direction)
            get_direction_to_move(ship, allowed_directions)

        fleet_move_chart[ship.id] = test_direction
        fleet_positions_next_turn[ship.id] = position_to_tuple(test_position)


ship_status = {}
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
    fleet_positions_next_turn = {}

    for ship in me.get_ships():
        assign_ship_status(ship)
        handle_ships_staying_to_harvest(ship)

    for ship in me.get_ships():
        get_direction_to_move(ship)

    for ship in me.get_ships():
        command_queue.append(ship.move(fleet_move_chart[ship.id]))

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game.turn_number <= 400 and \
            me.halite_amount >= constants.SHIP_COST \
            and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

