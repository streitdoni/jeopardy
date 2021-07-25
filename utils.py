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
import glob

import html
import os
import re
import string

from config import config
from model import ContentMedia, ViewAnswerType
from flask import render_template


def parse_questions(filename):
    """Parses a question file.
       Returns a dict (of categories) of lists of questions (in score order)
    """
    # TODO should drop the old format entirely?
    # if so use html and integrate answers into question file
    # people can then use asciidoctor or markdown to render questions from
    # a simpler format
    questions = {}
    cur_category = None
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.rstrip("\r\n")

                # skip comments or whitespace lines
                if re.match(r'^\s*(#|$)', line):
                    continue

                # it's a category
                m = re.match(r'^>(.*)$', line)
                if m:
                    # create category entry
                    questions[m.group(1)] = list()
                    cur_category = m.group(1)
                    continue

                # convert fake new-lines into real ones
                line = re.sub(r'\\n', '\n', line)

                # it's a question, split type and question
                question = {}
                questionContent = {}
                entries = line.split(';')
                question['description'] = entries[0]
                question['text'] = entries[1]
                i = 0
                for qContent in entries[2:]:
                    viewIdqTypeAndContent = qContent.split(':', 2)
                    questionContent[i] = {'viewId': viewIdqTypeAndContent[0], 'type': viewIdqTypeAndContent[1],
                                          'content': viewIdqTypeAndContent[2]}
                    i = i + 1

                question['content'] = questionContent
                questions[cur_category].append(question)

    except Exception as e:
        context = "Problem parsing the question file: {}".format(filename)
        raise QuestionParsingError(context)(e)

    return questions


def parse_answers(filename):
    """Parses a answer file.
       Returns a dict (of categories) of lists of questions (in score order)
    """
    # TODO should drop the old format entirely?
    # if so use html and integrate answers into question file
    # people can then use asciidoctor or markdown to render questions from
    # a simpler format
    answers = []
    cur_category = None
    try:
        with open(filename, 'r') as f:
            qId = 0
            for line in f:
                line = line.rstrip("\r\n")

                # skip comments or whitespace lines
                if re.match(r'^\s*(#|$)', line):
                    continue

                # it's a category
                m = re.match(r'^>(.*)$', line)
                if m:
                    continue

                # convert fake new-lines into real ones
                line = re.sub(r'\\n', '\n', line)

                # split answer in columns by ,'
                entries = line.split(';')

                answerContent = []
                for content in entries[1:]:
                    answer = {}
                    answer['text'] = entries[0]
                    mediaAndContent = content.split(':', 1)
                    answer['media'] = mediaAndContent[0]
                    answer['content'] = mediaAndContent[1]
                    answerContent.append(answer)

                answers.append(answerContent)

    except Exception as e:
        context = "Problem parsing the answer file: {}".format(filename)
        raise AnswerParsingError(context)(e)

    return answers


def parse_gamefile(filename):
    """Parses a game file. A game file holds the categories that are going to be
        played in order.
       Returns a list of category strings and a final question dict
    """
    # TODO should drop the old format entirely?
    # if so we need to be able to express final question somehow
    categories = list()
    final = None
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.rstrip("\r\n")

                # match: final: [category] text
                m = re.match(r'final: \[([^]]+)\] (.*)$', line)
                if m:
                    final = {'category': m.group(1), 'question': m.group(2)}
                    continue

                categories.append(line)

    except Exception as e:
        context = "Problem parsing the game file: {}".format(filename)
        raise GamefileParsingError(context)(e)

    return categories, final


def escape_html_conform(text):
    """Parses the questions from the Beopardy Game Board format"""
    text = html.escape(text)

    # Warning, we don't support nested line heading options
    # UTF-8 is just killed since everything is UTF-8 now
    if text.startswith('[utf8]'):
        text = text.lstrip('[utf8]')

    # Fixed width strings
    if text.startswith('[fixed]'):
        text = text.lstrip('[fixed]')
        text = "<tt>{}</tt>".format(text)

    # Transform new lines into <br>
    text = re.sub(r'\n', '<br/>', text)
    return text


def list_roundfiles():
    """List available roundfiles in config's data directory"""

    _glob = config['BASE_DIR'] + 'data/*.round'
    # return file names only
    return [os.path.basename(_f) for _f in glob.glob(_glob)]


def parse_question_id(qid):
    """
    Parses a question id in the form category X question Y and view Z(cXqYvZ) and
    returns a triple with category, question, and current view or None if it didn't work.
    """
    match = re.match("c([0-9]+)q([0-9]+)v([0-9])", qid)
    if match is None:
        raise InvalidQuestionId("Invalid Question Id: {}".format(qid))
    col, row, content = match.groups()
    return (col, row, content)


def deparse_question_id(qid, cid, vid):
    return 'c{}q{}v{}'.format(qid, cid, vid)


def render_answer_view(answerViewType, heading, answers):
    if answerViewType is ViewAnswerType.TextAndContent:
        return render_content_view(heading, answers)
    elif answerViewType is ViewAnswerType.ListOfText:

        htmlContent = ''
        htmlContent += '<div class="question-container">'
        escapedtext = escape_html_conform(heading)

        htmlContent += '<p class="question-and-content question-text">{}</p>'.format(escapedtext)
        if len(answers) > 0:
            num = 1
            htmlContent += '<div class="question-content-container">'
            for answer in answers:
                htmlContent += '<p class="answer-text-list-content answer-content-list-text-item">{}. {}</p>'.format(
                    num,
                    answer.content)
                num = num + 1
            htmlContent += '</div>'
        htmlContent += '</div>'
        return htmlContent


def render_content_view(heading, content, category=None):
    htmlContent = ''
    htmlContent += '<div class="question-container">'
    escapedtext = escape_html_conform(heading)

    htmlContent += '<p class="question-and-content question-text">{}</p>'.format(escapedtext)
    if len(content) > 0:
        htmlContent += '<div class="question-content-container">'
        for entry in content:
            width_class = 'question-view-mh-100'
            if len(content) > 3:
                width_class = 'question-view-mh-50'

            if entry.media is ContentMedia.image:
                htmlContent += '<img class="question-and-content {}" src="{}{}"/>'.format(width_class,
                                                                                          config['IMAGES_FOLDER'],
                                                                                          entry.content)
            elif entry.media is ContentMedia.text:
                escapedtext = escape_html_conform(entry.content)
                htmlContent += '<p class="question-and-content question-content-text {}">{}</p>'.format(width_class,
                                                                                                        escapedtext)
            elif entry.media is ContentMedia.music:
                htmlContent += '<img class="question-and-content {}" src="{}"/><audio id="currentQuestionSound" src="{}{}" type="audio/mp3" preload="auto"></audio>'.format(
                    width_class, config['SOUND_ANIMATION'], config['SOUNDS_FOLDER'], entry.content)
        htmlContent += '</div>'
    htmlContent += '</div>'
    if category:
        return {'content': htmlContent, 'category': category}
    else:
        return htmlContent


class InvalidQuestionId(Exception):
    pass


class QuestionParsingError(Exception):
    pass


class AnswerParsingError(Exception):
    pass


class GamefileParsingError(Exception):
    pass
