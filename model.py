# Ceopardy
# https://github.com/obilodeau/ceopardy/
#
# Olivier Bilodeau <olivier@bottomlesspit.org>
# Copyright (C) 2017 Olivier Bilodeau
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
import collections
from enum import Enum

from flask import current_app as app

from ceopardy import db, VERSION

SCHEMA_VERSION = 1


# TODO save a game in progress
# TODO load a game in progress
# TODO refactor to GameModel?


class GameState(Enum):
    uninitialized = 0
    in_round = 1
    in_final = 2
    finished = 3


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.Enum(GameState))
    ceopardy_version = db.Column(db.String(16))
    schema_version = db.Column(db.Integer)
    round_filename = db.Column(db.String(255))

    def __init__(self):
        self.state = GameState.uninitialized
        self.ceopardy_version = VERSION
        self.schema_version = SCHEMA_VERSION

    def __repr__(self):
        return '<Game in state %r>' % self.state


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tid = db.Column(db.String(7), unique=True)
    name = db.Column(db.String(80), unique=True)
    handicap = db.Column(db.Integer)

    answers = db.relationship('Answer', back_populates='team')

    def __init__(self, tid, name, handicap=0):
        self.tid = tid
        self.name = name
        self.handicap = handicap
        app.logger.debug("Team created: name is {}, handicap is {}"
                         .format(self.name, self.handicap))

    def __repr__(self):
        return '<Team %r>' % self.name


class QuestionType(Enum):
    Standard = 'S'
    image = 2
    text = 3


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    score_original = db.Column(db.Integer)
    category = db.Column(db.String(80))
    final = db.Column(db.Boolean)
    double = db.Column(db.Boolean)
    row = db.Column(db.Integer)
    col = db.Column(db.Integer)

    answers = db.relationship('Answer', back_populates="question")
    questionContents = db.relationship('QuestionContent')

    def __init__(self, text, description, score_original, category, row, col, final=False,
                 double=False):
        self.text = text
        self.description = description
        self.score_original = score_original
        self.category = category
        self.row = row
        self.col = col
        self.final = final
        self.double = double

    def __repr__(self):
        return '<Question {} for {} at col {} row {}>' \
            .format(self.category, self.score_original, self.col, self.row)


class QuestionMedia(Enum):
    music = 1
    image = 2
    text = 3


class QuestionContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    viewid = db.Column(db.Integer, nullable=False)
    media = db.Column(db.Enum(QuestionMedia), nullable=False)
    content = db.Column(db.String(255), nullable=False)

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    question = db.relationship('Question', back_populates="questionContents")

    def __init__(self, viewid, media, content, question):
        self.viewid = viewid
        self.media = media
        self.content = content
        self.question = question


# For the database, a final question is just a flag on a regular question.
# This convenience object is created so that we manage it in a more OO-ish way
# after parsing and before database insertion.
FinalQuestion = collections.namedtuple('FinalQuestion', 'category question')


class Response(Enum):
    bad = -1
    nop = 0
    good = 1


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score_attributed = db.Column(db.Integer)
    response = db.Column(db.Enum(Response))

    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    team = db.relationship('Team', back_populates="answers")

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    question = db.relationship('Question', back_populates="answers")

    def __init__(self, response, team, question):
        """Meant to be used on normal questions where score is not changeable"""
        self.score_attributed = question.score_original
        self.response = response
        self.team = team
        self.question = question

    def __repr__(self):
        return '<Answer by team id {} to question id {} is {}. Points {}>' \
            .format(self.team_id, self.question_id, self.response.name,
                    self.score_attributed)


class Category():
    def __init__(self, value, column):
        self.value = value
        self.column = column


class State(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), unique=True)
    value = db.Column(db.String(4096))

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return '<State {} is {}.>'.format(self.name, self.value)


# This creates the database if it doesn't already exist
db.create_all()
