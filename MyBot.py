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


total_halite = get_total_halite(game.game_map)
number_of_players = len(list(game.players.keys()))
REVENUE_EXPECTATION = 4000
SHIP_UPPER_LIMIT = total_halite / (number_of_players * REVENUE_EXPECTATION)
SHIP_LOWER_LIMIT = 5
SPAWN_TURN_LIMIT = 250
NUMBER_OF_TURNS_SUPPRESS_ALL_SPAWNS = 20
HARVEST_HALITE_LOWER_LIMIT = 10
DIRECTION_STAY = (0,0)
ROLLUP_TURN_BUFFER = 7

ship_status = {}
ship_destination = {}  # used for going to regions of most halite
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
        move = determine_move(ship)
        if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full:
            command_queue.append(ship.move(move))
        else:
            command_queue.append(ship.stay_still())

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

        ship_at_shipyard_goes_hella_halite(ship)
        validate_heading_hella_halite_status(ship)
        check_rollup(ship)

        if ship_status[ship.id] == 'exploring':
            move = get_move_exploring(ship)

        if ship_status[ship.id] == 'heading_hella_halite':
            move = get_move_hella_halite(ship)

        if ship.is_full or ship_status[ship.id] == 'returning':
            move = get_move_returning_ship(ship)
            
        if ship_status[ship.id] == 'rollup':
            move = get_move_rollup()

        return move


    def validate_heading_hella_halite_status(ship):
        if ship_status[ship.id] == 'heading_hella_halite':
            if ship_destination.get(ship.id) is None:
                ship_destination[ship.id] = get_position_most_halite()
            if game_map.calculate_distance(ship.position, ship_destination[ship.id]) <= 1:
                ship_status[ship.id] = 'exploring'


    def ship_at_shipyard_goes_hella_halite(ship):
        if ship.position == me.shipyard.position or ship.id not in ship_status:
            ship_status[ship.id] = 'heading_hella_halite'
            ship_destination[ship.id] = get_position_most_halite()


    def get_move_exploring(ship):
        ship_status[ship.id] = 'exploring'
        directions = find_safe_directions(ship)
        move = find_direction_most_halite(directions)
        claim_location(move)
        return move


    def get_move_returning_ship(ship):
        ship_status[ship.id] = 'returning'
        return_move = smart_navigate(ship, me.shipyard.position)
        claim_location(return_move)
        return return_move

    def get_move_hella_halite(ship):
        ship_status[ship.id] = 'heading_hella_halite'
        move = smart_navigate(ship, ship_destination[ship.id])
        claim_location(move)
        return move


    def get_move_rollup():
        ship_status[ship.id] = 'rollup'
        move = smart_navigate(ship, ship_destination[ship.id])
        return move


    def find_safe_directions(ship):
        if ship_status[ship.id] == 'exploring':
            directions = [Direction.North, Direction.South, Direction.East, Direction.West, DIRECTION_STAY]
        else:
            directions = [Direction.North, Direction.South, Direction.East, Direction.West]
        safe_directions = []
        for direction in directions:
            test_location = ship.position.directional_offset(direction)
            if not game_map[test_location].is_occupied and test_location not in list(claimed_locations.values()):
                safe_directions.append(direction)
        return safe_directions

    def find_direction_most_halite(directions):
        if len(directions) == 0 or get_halite_in_direction(DIRECTION_STAY) >= HARVEST_HALITE_LOWER_LIMIT:
            return DIRECTION_STAY
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


    def claim_location(move):
        claimed_locations[ship.id] = ship.position.directional_offset(move)
        game_map[ship.position.directional_offset(move)].mark_unsafe(ship)

    def smart_navigate(ship, destination):
        safe_directions = find_safe_directions(ship)
        if len(safe_directions) == 0:
            return DIRECTION_STAY

        min_distance = 1000
        best_direction = random.choice(safe_directions)
        for direction in safe_directions:
            test_location = ship.position.directional_offset(direction)
            distance = game_map.calculate_distance(test_location, destination)
            if distance < min_distance:
                min_distance = distance
                best_direction = direction
            if distance == min_distance:
                best_direction = random.choice([direction, best_direction])
        return best_direction

    def calculate_distance_tuple(location_1, location_2):
        return location_1[0] - location_2[0], location_1[1] - location_2[1]

    def get_position_most_halite():
        most_halite_at_a_position = 0
        for x_pos in range(game_map.width):
            for y_pos in range(game_map.height):
                test_position = Position(x_pos, y_pos)
                test_position_halite_amount = game_map[test_position].halite_amount
                if test_position_halite_amount > most_halite_at_a_position:
                    most_halite_at_a_position = test_position_halite_amount
                    position_most_halite =test_position
        return position_most_halite

    def check_rollup(ship):
        number_of_turns_to_return_to_shipyard = game_map.calculate_distance(ship.position, me.shipyard.position)
        if constants.MAX_TURNS - game.turn_number - number_of_turns_to_return_to_shipyard <= ROLLUP_TURN_BUFFER:
            ship_status[ship.id] = 'rollup'
            ship_destination[ship.id] = me.shipyard.position

    # def map_halite():
    #     game_height = game_map.height
    #     game_width = game_map.width
    #     halite_map = [[]]
    #
    #     for x_pos in range(game_width):
    #         for y_pos in range (game_height):
    #             halite_map[x_pos, y_pos] = game_map[(x_pos, y_pos)].halite_amount
    #     return halite_map
