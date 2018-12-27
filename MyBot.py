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


def handle_ships_staying_to_harvest(ship):
    current_ship_position = ship.position
    if game_map[current_ship_position].halite_amount > 0 and not ship.is_full:
        fleet_move_chart[ship.id] = Direction.Still
        fleet_positions_next_turn.append(ship.position)


def get_direction_to_move(ship, allowed_directions=None):
    if ship.id not in fleet_move_chart.keys():

        if allowed_directions is None:
            allowed_directions = [Direction.North, Direction.South, Direction.East, Direction.West]

        test_direction = random.choice(allowed_directions)
        test_position = ship.position.directional_offset(test_direction)

        if test_position in fleet_positions_next_turn:
            allowed_directions.remove(test_direction)
            get_direction_to_move(ship, allowed_directions)

        fleet_move_chart[ship.id] = test_direction
        fleet_positions_next_turn.append(test_position)


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
        handle_ships_staying_to_harvest(ship)

    for ship in me.get_ships():
        get_direction_to_move(ship)

    for ship in me.get_ships():
        command_queue.append(ship.move(fleet_move_chart[ship.id]))

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

