#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
from typing import List, Any

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
game.ready("LikeABotOutOfHalite")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """
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
    claimed_locations = {}
    for ship in me.get_ships():
        # For each of your ships, move randomly if the ship is on a low halite location or the ship is full.
        #   Else, collect halite.
        move = determine_move()
        if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full:
            command_queue.append(ship.move(move))
        else:
            command_queue.append(ship.stay_still())

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game.turn_number <= 300 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)


    def determine_move():
        if ship.id not in ship_status:
            ship_status[ship.id] = 'exploring'

        if ship.is_full or ship_status[ship.id] == 'returning':
            if ship.position == me.shipyard.position:
                move = get_move_exploring()
            else:
                move = get_move_returning_ship()

        else:
            move = get_move_exploring()
        return move


    def get_move_exploring():
        ship_status[ship.id] = 'exploring'
        directions = find_safe_directions()
        move = find_direction_most_halite(directions)
        claim_location(move)
        return move


    def get_move_returning_ship():
        ship_status[ship.id] = 'returning'
        return_move = game_map.naive_navigate(ship, me.shipyard.position)
        claim_location(return_move)
        return return_move

    def find_safe_directions():
        directions = [Direction.North, Direction.South, Direction.East, Direction.West]
        safe_directions = []
        for direction in directions:
            test_location = ship.position.directional_offset(direction)
            if not game_map[test_location].is_occupied and test_location not in list(claimed_locations.values()):
                safe_directions.append(direction)
        return safe_directions

    def find_direction_most_halite(directions):
        if len(directions) == 0:
            return (0,0)
        max_halite_found = 0
        best_direction = random.choice(directions)
        for direction in directions:
            test_location = ship.position.directional_offset(direction)
            test_halite_amount = game_map[test_location].halite_amount
            if test_halite_amount > max_halite_found:
                max_halite_found = test_halite_amount
                best_direction = direction
        return best_direction

    def claim_location(move):
        claimed_locations[ship.id] = ship.position.directional_offset(move)
        game_map[ship.position.directional_offset(move)].mark_unsafe(ship)
