#!/usr/bin/python

import argparse
import sys
sys.path.append("../../platform/build/bindings/python/")
sys.path.append("../../platform/bindings/python/")
from libpydiamond import *
import ReactiveManager

def main():
    parser = argparse.ArgumentParser(description='Play a silly game.')
    parser.add_argument('name', help='your name')
    parser.add_argument('config_prefix', help='frontend config file prefix')
    args = parser.parse_args()

    DiamondInit(args.config_prefix, 0, 1);

    myName = args.name

    players = DStringList()
    move = DCounter()
    DStringList.Map(players, "simplegame:players")
    DCounter.Map(move, "simplegame:move")

    ReactiveManager.txn_execute(addPlayer, players, myName)

    ReactiveManager.add(displayGame, players, move, myName)

    while True:
        words = sys.stdin.readline().split()
        if words[0].lower() == "reset".lower():
            ReactiveManager.txn_execute(resetGame, players, move)
        elif words[0].lower() == "exit".lower():
            sys.exit()
        else:
            action = int(words[0])
            ReactiveManager.txn_execute(takeTurn, players, move, myName, action)

def resetGame(players, move):
    move.Set(0)
    for name in players.Members():
        score = DLong()
        DLong.Map(score, "simplegame:" + name + ":score")
        score.Set(0)

def addPlayer(players, name):
    if players.Index(name) == -1:
        players.Append(name)

def takeTurn(players, move, name, incr):
    currentPlayer = players.Value(move.Value() % players.Size())
    if currentPlayer == name:
        score = DLong()
        DLong.Map(score, "simplegame:" + name + ":score")
        score.Set(score.Value() + incr)
        move.Set(move.Value() + 1)

def displayGame(players, move, myName):
    for name in players.Members():
        score = DLong()
        DLong.Map(score, "simplegame:" + name + ":score")
        print "Player: " + name + " score: " + repr(score.Value())
    currentPlayer = players.Value(move.Value() % players.Size())
    if currentPlayer == myName:
        print "It's your turn! Enter your move:"
    else:
        print "It's " + currentPlayer + "'s turn"

if __name__ == "__main__": main()