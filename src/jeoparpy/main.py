#!/usr/bin/python
"""
main.pyw
Author: Adam Beagle

DESCRIPTION:
  Entry point for the JeoparPy application.
  Initialization, primary game loop, and event handlers are here.
  Serves as interface between 'game' and 'ui' packages.

Copyright (C) 2013 Adam Beagle - All Rights Reserved
You may use, distribute, and modify this code under
the terms of the GNU General Public License,
viewable at http://opensource.org/licenses/GPL-3.0

This copyright notice must be retained with any use
of source code from this file.

"""

import pygame
from pygame.locals import *

from config import FPS_LIMIT, FULLSCREEN, SUBTRACT_ON_INCORRECT, SCREEN_SIZE
from constants import ANIMATIONEND, ANSWER_TIMEOUT, AUDIOEND, SKIP_INTRO_FLAG
from game import GameData, JeopGameState
from ui import Controller, do_congrats, do_credits, do_intro, do_scroll

EVENTS_ALLOWED = (ANIMATIONEND, ANSWER_TIMEOUT,
                  AUDIOEND, KEYDOWN, MOUSEBUTTONDOWN, QUIT)

###############################################################################
def main(*flags):
    """Entry point."""
   
    # Initialization
    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE,
                                     pygame.FULLSCREEN if FULLSCREEN else 0)
    pygame.display.set_caption('JeoparPy!')

    # Declarations
    gameData = GameData()
    gs = JeopGameState()
    uicontroller = Controller(screen, gameData, FPS_LIMIT)
    clock = pygame.time.Clock()

    # Intro sequence (control passed completely to functions)
    if SKIP_INTRO_FLAG not in flags:
        pygame.mouse.set_visible(0)
        do_intro(screen, clock, uicontroller.audioplayer)
        do_scroll(screen, clock, gameData.categories)
        pygame.mouse.set_visible(1)

    # Prep for primary loop
    pygame.event.set_allowed(None)
    pygame.event.set_allowed(EVENTS_ALLOWED)
    uicontroller.draw(screen)

    # Primary loop
    while not gs.state == gs.GAME_END:
        # Events
        handle_events(gs, gameData, uicontroller)
        if gs.state == gs.QUIT:
            return

        # Update
        gameData.update(gs)
        uicontroller.update(gs, gameData)
        gs.transition_state_immediate_linear(gameData)
        transition_state_branching(gs, gameData, uicontroller)

        # Draw
        uicontroller.draw(screen)

        # Cleanup
        pygame.event.pump()
        clock.tick_busy_loop(FPS_LIMIT)

    # Post game: Congratulations screen and credits
    pygame.mouse.set_visible(0)
    do_congrats(screen, clock, gameData.winners, uicontroller.audioplayer)
    do_credits(screen, clock, uicontroller.audioplayer, FPS_LIMIT)
    
###############################################################################
def handle_events(gameState, gameData, uicontroller):
    gs = gameState
    for event in pygame.event.get():
        if event.type == QUIT:
            gs.state = gs.QUIT

        elif event.type == KEYDOWN:
            handle_event_key(event, gameState, gameData)

        elif event.type == MOUSEBUTTONDOWN:
            handle_event_mousebuttondown(event, gameState, uicontroller)

        elif event.type == ANIMATIONEND:
            handle_event_animationend(event, gameState)
            
        elif event.type == ANSWER_TIMEOUT and gs.state == gs.WAIT_BUZZ_IN:
            gs.state = gs.ANSWER_TIMEOUT

        elif event.type == ANSWER_TIMEOUT and gs.state == gs.WAIT_ANSWER:
            gs.state = (gs.ANSWER_INCORRECT, gs.arg)

        elif event.type == AUDIOEND and gs.state == gs.WAIT_CLUE_READ:
            if uicontroller.clue_is_audioclue(gs.arg):
                gs.state = (gs.PLAY_CLUE_AUDIO, gs.arg)
            else:
                gs.state = (gs.START_CLUE_TIMER, gameData.amounts[gs.arg[1]])

def handle_event_animationend(event, gameState):
    gs = gameState

    if gs.state == gs.WAIT_BOARD_FILL:
        gs.state = gs.WAIT_CHOOSE_CLUE

    elif gs.state == gs.WAIT_CLUE_OPEN:
        gs.state = (gs.CLUE_OPEN, gs.arg)
        
def handle_event_key(event, gameState, gameData):
    gs = gameState
    
    if event.key == K_q:
        if pygame.key.get_mods() & KMOD_SHIFT:
            gs.state = gs.QUIT
        else:
            gs.state = gs.GAME_END

    elif gs.state == gs.WAIT_TRIGGER_AUDIO and event.key == K_m:
        gs.state = (gs.PLAY_CLUE_AUDIO, gs.arg)

    elif gs.state == gs.WAIT_BUZZ_IN and event.key in (K_1, K_2, K_3):
        p = event.key - K_1
        if not gameData.players[p].hasAnswered:
            gs.state = (gs.BUZZ_IN, (p, gs.arg))
            
    elif gs.state == gs.WAIT_BUZZ_IN and event.key == K_END:
        gs.state = gs.ANSWER_TIMEOUT

    elif gs.state == gs.WAIT_ANSWER:
        if event.key == K_SPACE:
            gs.state = (gs.ANSWER_CORRECT, gs.arg)
        elif event.key == K_BACKSPACE:
            gs.state = (gs.ANSWER_INCORRECT, gs.arg)

def handle_event_mousebuttondown(event, gameState, uicontroller):
    gs = gameState

    if gs.state == gs.WAIT_CHOOSE_CLUE and event.button == 1:
        clueCoords = uicontroller.get_clicked_clue(event.pos)

        if clueCoords:
            gs.state = (gs.CLICK_CLUE, clueCoords)

def transition_state_branching(gameState, gameData, uicontroller):
    """
    Handle any state transitions whose next state is determined
    by branching on UI or data conditions.
    """
    gs = gameState
        
    if gs.state == gs.CLUE_OPEN:
        if uicontroller.clue_has_audio_reading(gs.arg):
            gs.state = (gs.WAIT_CLUE_READ, gs.arg)
            
        elif uicontroller.clue_is_audioclue(gs.arg):
            gs.state = (gs.WAIT_TRIGGER_AUDIO, gs.arg)
        else:
            gs.state = (gs.START_CLUE_TIMER, gameData.amounts[gs.arg[1]])

    elif gs.state == gs.ANSWER_INCORRECT:
        if gameData.allPlayersAnswered:
            gs.state = gs.ANSWER_NONE
        else:
            gs.state = (gs.START_CLUE_TIMER, gs.arg[1])
