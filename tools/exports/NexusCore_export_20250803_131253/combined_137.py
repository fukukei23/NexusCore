
# === NexusCore/tools\exports\export_20250803_114325\combined_40.py ===

# === NexusCore/openenv\Lib\site-packages\pycparser\ply\yacc.py ===
# -----------------------------------------------------------------------------
# ply: yacc.py
#
# Copyright (C) 2001-2017
# David M. Beazley (Dabeaz LLC)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of the David Beazley or Dabeaz LLC may be used to
#   endorse or promote products derived from this software without
#  specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------
#
# This implements an LR parser that is constructed from grammar rules defined
# as Python functions. The grammer is specified by supplying the BNF inside
# Python documentation strings.  The inspiration for this technique was borrowed
# from John Aycock's Spark parsing system.  PLY might be viewed as cross between
# Spark and the GNU bison utility.
#
# The current implementation is only somewhat object-oriented. The
# LR parser itself is defined in terms of an object (which allows multiple
# parsers to co-exist).  However, most of the variables used during table
# construction are defined in terms of global variables.  Users shouldn't
# notice unless they are trying to define multiple parsers at the same
# time using threads (in which case they should have their head examined).
#
# This implementation supports both SLR and LALR(1) parsing.  LALR(1)
# support was originally implemented by Elias Ioup (ezioup@alumni.uchicago.edu),
# using the algorithm found in Aho, Sethi, and Ullman "Compilers: Principles,
# Techniques, and Tools" (The Dragon Book).  LALR(1) has since been replaced
# by the more efficient DeRemer and Pennello algorithm.
#
# :::::::: WARNING :::::::
#
# Construction of LR parsing tables is fairly complicated and expensive.
# To make this module run fast, a *LOT* of work has been put into
# optimization---often at the expensive of readability and what might
# consider to be good Python "coding style."   Modify the code at your
# own risk!
# ----------------------------------------------------------------------------

import re
import types
import sys
import os.path
import inspect
import base64
import warnings

__version__    = '3.10'
__tabversion__ = '3.10'

#-----------------------------------------------------------------------------
#                     === User configurable parameters ===
#
# Change these to modify the default behavior of yacc (if you wish)
#-----------------------------------------------------------------------------

yaccdebug   = True             # Debugging mode.  If set, yacc generates a
                               # a 'parser.out' file in the current directory

debug_file  = 'parser.out'     # Default name of the debugging file
tab_module  = 'parsetab'       # Default name of the table module
default_lr  = 'LALR'           # Default LR table generation method

error_count = 3                # Number of symbols that must be shifted to leave recovery mode

yaccdevel   = False            # Set to True if developing yacc.  This turns off optimized
                               # implementations of certain functions.

resultlimit = 40               # Size limit of results when running in debug mode.

pickle_protocol = 0            # Protocol to use when writing pickle files

# String type-checking compatibility
if sys.version_info[0] < 3:
    string_types = basestring
else:
    string_types = str

MAXINT = sys.maxsize

# This object is a stand-in for a logging object created by the
# logging module.   PLY will use this by default to create things
# such as the parser.out file.  If a user wants more detailed
# information, they can create their own logging object and pass
# it into PLY.

class PlyLogger(object):
    def __init__(self, f):
        self.f = f

    def debug(self, msg, *args, **kwargs):
        self.f.write((msg % args) + '\n')

    info = debug

    def warning(self, msg, *args, **kwargs):
        self.f.write('WARNING: ' + (msg % args) + '\n')

    def error(self, msg, *args, **kwargs):
        self.f.write('ERROR: ' + (msg % args) + '\n')

    critical = debug

# Null logger is used when no output is generated. Does nothing.
class NullLogger(object):
    def __getattribute__(self, name):
        return self

    def __call__(self, *args, **kwargs):
        return self

# Exception raised for yacc-related errors
class YaccError(Exception):
    pass

# Format the result message that the parser produces when running in debug mode.
def format_result(r):
    repr_str = repr(r)
    if '\n' in repr_str:
        repr_str = repr(repr_str)
    if len(repr_str) > resultlimit:
        repr_str = repr_str[:resultlimit] + ' ...'
    result = '<%s @ 0x%x> (%s)' % (type(r).__name__, id(r), repr_str)
    return result

# Format stack entries when the parser is running in debug mode
def format_stack_entry(r):
    repr_str = repr(r)
    if '\n' in repr_str:
        repr_str = repr(repr_str)
    if len(repr_str) < 16:
        return repr_str
    else:
        return '<%s @ 0x%x>' % (type(r).__name__, id(r))

# Panic mode error recovery support.   This feature is being reworked--much of the
# code here is to offer a deprecation/backwards compatible transition

_errok = None
_token = None
_restart = None
_warnmsg = '''PLY: Don't use global functions errok(), token(), and restart() in p_error().
Instead, invoke the methods on the associated parser instance:

    def p_error(p):
        ...
        # Use parser.errok(), parser.token(), parser.restart()
        ...

    parser = yacc.yacc()
'''

def errok():
    warnings.warn(_warnmsg)
    return _errok()

def restart():
    warnings.warn(_warnmsg)
    return _restart()

def token():
    warnings.warn(_warnmsg)
    return _token()

# Utility function to call the p_error() function with some deprecation hacks
def call_errorfunc(errorfunc, token, parser):
    global _errok, _token, _restart
    _errok = parser.errok
    _token = parser.token
    _restart = parser.restart
    r = errorfunc(token)
    try:
        del _errok, _token, _restart
    except NameError:
        pass
    return r

#-----------------------------------------------------------------------------
#                        ===  LR Parsing Engine ===
#
# The following classes are used for the LR parser itself.  These are not
# used during table construction and are independent of the actual LR
# table generation algorithm
#-----------------------------------------------------------------------------

# This class is used to hold non-terminal grammar symbols during parsing.
# It normally has the following attributes set:
#        .type       = Grammar symbol type
#        .value      = Symbol value
#        .lineno     = Starting line number
#        .endlineno  = Ending line number (optional, set automatically)
#        .lexpos     = Starting lex position
#        .endlexpos  = Ending lex position (optional, set automatically)

class YaccSymbol:
    def __str__(self):
        return self.type

    def __repr__(self):
        return str(self)

# This class is a wrapper around the objects actually passed to each
# grammar rule.   Index lookup and assignment actually assign the
# .value attribute of the underlying YaccSymbol object.
# The lineno() method returns the line number of a given
# item (or 0 if not defined).   The linespan() method returns
# a tuple of (startline,endline) representing the range of lines
# for a symbol.  The lexspan() method returns a tuple (lexpos,endlexpos)
# representing the range of positional information for a symbol.

class YaccProduction:
    def __init__(self, s, stack=None):
        self.slice = s
        self.stack = stack
        self.lexer = None
        self.parser = None

    def __getitem__(self, n):
        if isinstance(n, slice):
            return [s.value for s in self.slice[n]]
        elif n >= 0:
            return self.slice[n].value
        else:
            return self.stack[n].value

    def __setitem__(self, n, v):
        self.slice[n].value = v

    def __getslice__(self, i, j):
        return [s.value for s in self.slice[i:j]]

    def __len__(self):
        return len(self.slice)

    def lineno(self, n):
        return getattr(self.slice[n], 'lineno', 0)

    def set_lineno(self, n, lineno):
        self.slice[n].lineno = lineno

    def linespan(self, n):
        startline = getattr(self.slice[n], 'lineno', 0)
        endline = getattr(self.slice[n], 'endlineno', startline)
        return startline, endline

    def lexpos(self, n):
        return getattr(self.slice[n], 'lexpos', 0)

    def lexspan(self, n):
        startpos = getattr(self.slice[n], 'lexpos', 0)
        endpos = getattr(self.slice[n], 'endlexpos', startpos)
        return startpos, endpos

    def error(self):
        raise SyntaxError

# -----------------------------------------------------------------------------
#                               == LRParser ==
#
# The LR Parsing engine.
# -----------------------------------------------------------------------------

class LRParser:
    def __init__(self, lrtab, errorf):
        self.productions = lrtab.lr_productions
        self.action = lrtab.lr_action
        self.goto = lrtab.lr_goto
        self.errorfunc = errorf
        self.set_defaulted_states()
        self.errorok = True

    def errok(self):
        self.errorok = True

    def restart(self):
        del self.statestack[:]
        del self.symstack[:]
        sym = YaccSymbol()
        sym.type = '$end'
        self.symstack.append(sym)
        self.statestack.append(0)

    # Defaulted state support.
    # This method identifies parser states where there is only one possible reduction action.
    # For such states, the parser can make a choose to make a rule reduction without consuming
    # the next look-ahead token.  This delayed invocation of the tokenizer can be useful in
    # certain kinds of advanced parsing situations where the lexer and parser interact with
    # each other or change states (i.e., manipulation of scope, lexer states, etc.).
    #
    # See:  https://www.gnu.org/software/bison/manual/html_node/Default-Reductions.html#Default-Reductions
    def set_defaulted_states(self):
        self.defaulted_states = {}
        for state, actions in self.action.items():
            rules = list(actions.values())
            if len(rules) == 1 and rules[0] < 0:
                self.defaulted_states[state] = rules[0]

    def disable_defaulted_states(self):
        self.defaulted_states = {}

    def parse(self, input=None, lexer=None, debug=False, tracking=False, tokenfunc=None):
        if debug or yaccdevel:
            if isinstance(debug, int):
                debug = PlyLogger(sys.stderr)
            return self.parsedebug(input, lexer, debug, tracking, tokenfunc)
        elif tracking:
            return self.parseopt(input, lexer, debug, tracking, tokenfunc)
        else:
            return self.parseopt_notrack(input, lexer, debug, tracking, tokenfunc)


    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # parsedebug().
    #
    # This is the debugging enabled version of parse().  All changes made to the
    # parsing engine should be made here.   Optimized versions of this function
    # are automatically created by the ply/ygen.py script.  This script cuts out
    # sections enclosed in markers such as this:
    #
    #      #--! DEBUG
    #      statements
    #      #--! DEBUG
    #
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def parsedebug(self, input=None, lexer=None, debug=False, tracking=False, tokenfunc=None):
        #--! parsedebug-start
        lookahead = None                         # Current lookahead symbol
        lookaheadstack = []                      # Stack of lookahead symbols
        actions = self.action                    # Local reference to action table (to avoid lookup on self.)
        goto    = self.goto                      # Local reference to goto table (to avoid lookup on self.)
        prod    = self.productions               # Local reference to production list (to avoid lookup on self.)
        defaulted_states = self.defaulted_states # Local reference to defaulted states
        pslice  = YaccProduction(None)           # Production object passed to grammar rules
        errorcount = 0                           # Used during error recovery

        #--! DEBUG
        debug.info('PLY: PARSE DEBUG START')
        #--! DEBUG

        # If no lexer was given, we will try to use the lex module
        if not lexer:
            from . import lex
            lexer = lex.lexer

        # Set up the lexer and parser objects on pslice
        pslice.lexer = lexer
        pslice.parser = self

        # If input was supplied, pass to lexer
        if input is not None:
            lexer.input(input)

        if tokenfunc is None:
            # Tokenize function
            get_token = lexer.token
        else:
            get_token = tokenfunc

        # Set the parser() token method (sometimes used in error recovery)
        self.token = get_token

        # Set up the state and symbol stacks

        statestack = []                # Stack of parsing states
        self.statestack = statestack
        symstack   = []                # Stack of grammar symbols
        self.symstack = symstack

        pslice.stack = symstack         # Put in the production
        errtoken   = None               # Err token

        # The start state is assumed to be (0,$end)

        statestack.append(0)
        sym = YaccSymbol()
        sym.type = '$end'
        symstack.append(sym)
        state = 0
        while True:
            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer

            #--! DEBUG
            debug.debug('')
            debug.debug('State  : %s', state)
            #--! DEBUG

            if state not in defaulted_states:
                if not lookahead:
                    if not lookaheadstack:
                        lookahead = get_token()     # Get the next token
                    else:
                        lookahead = lookaheadstack.pop()
                    if not lookahead:
                        lookahead = YaccSymbol()
                        lookahead.type = '$end'

                # Check the action table
                ltype = lookahead.type
                t = actions[state].get(ltype)
            else:
                t = defaulted_states[state]
                #--! DEBUG
                debug.debug('Defaulted state %s: Reduce using %d', state, -t)
                #--! DEBUG

            #--! DEBUG
            debug.debug('Stack  : %s',
                        ('%s . %s' % (' '.join([xx.type for xx in symstack][1:]), str(lookahead))).lstrip())
            #--! DEBUG

            if t is not None:
                if t > 0:
                    # shift a symbol on the stack
                    statestack.append(t)
                    state = t

                    #--! DEBUG
                    debug.debug('Action : Shift and goto state %s', t)
                    #--! DEBUG

                    symstack.append(lookahead)
                    lookahead = None

                    # Decrease error count on successful shift
                    if errorcount:
                        errorcount -= 1
                    continue

                if t < 0:
                    # reduce a symbol on the stack, emit a production
                    p = prod[-t]
                    pname = p.name
                    plen  = p.len

                    # Get production function
                    sym = YaccSymbol()
                    sym.type = pname       # Production name
                    sym.value = None

                    #--! DEBUG
                    if plen:
                        debug.info('Action : Reduce rule [%s] with %s and goto state %d', p.str,
                                   '['+','.join([format_stack_entry(_v.value) for _v in symstack[-plen:]])+']',
                                   goto[statestack[-1-plen]][pname])
                    else:
                        debug.info('Action : Reduce rule [%s] with %s and goto state %d', p.str, [],
                                   goto[statestack[-1]][pname])

                    #--! DEBUG

                    if plen:
                        targ = symstack[-plen-1:]
                        targ[0] = sym

                        #--! TRACKING
                        if tracking:
                            t1 = targ[1]
                            sym.lineno = t1.lineno
                            sym.lexpos = t1.lexpos
                            t1 = targ[-1]
                            sym.endlineno = getattr(t1, 'endlineno', t1.lineno)
                            sym.endlexpos = getattr(t1, 'endlexpos', t1.lexpos)
                        #--! TRACKING

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated
                        # below as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            del symstack[-plen:]
                            self.state = state
                            p.callable(pslice)
                            del statestack[-plen:]
                            #--! DEBUG
                            debug.info('Result : %s', format_result(pslice[0]))
                            #--! DEBUG
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)    # Save the current lookahead token
                            symstack.extend(targ[1:-1])         # Put the production slice back on the stack
                            statestack.pop()                    # Pop back one state (before the reduce)
                            state = statestack[-1]
                            sym.type = 'error'
                            sym.value = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = False

                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                    else:

                        #--! TRACKING
                        if tracking:
                            sym.lineno = lexer.lineno
                            sym.lexpos = lexer.lexpos
                        #--! TRACKING

                        targ = [sym]

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated
                        # above as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            self.state = state
                            p.callable(pslice)
                            #--! DEBUG
                            debug.info('Result : %s', format_result(pslice[0]))
                            #--! DEBUG
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)    # Save the current lookahead token
                            statestack.pop()                    # Pop back one state (before the reduce)
                            state = statestack[-1]
                            sym.type = 'error'
                            sym.value = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = False

                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                if t == 0:
                    n = symstack[-1]
                    result = getattr(n, 'value', None)
                    #--! DEBUG
                    debug.info('Done   : Returning %s', format_result(result))
                    debug.info('PLY: PARSE DEBUG END')
                    #--! DEBUG
                    return result

            if t is None:

                #--! DEBUG
                debug.error('Error  : %s',
                            ('%s . %s' % (' '.join([xx.type for xx in symstack][1:]), str(lookahead))).lstrip())
                #--! DEBUG

                # We have some kind of parsing error here.  To handle
                # this, we are going to push the current token onto
                # the tokenstack and replace it with an 'error' token.
                # If there are any synchronization rules, they may
                # catch it.
                #
                # In addition to pushing the error token, we call call
                # the user defined p_error() function if this is the
                # first syntax error.  This function is only called if
                # errorcount == 0.
                if errorcount == 0 or self.errorok:
                    errorcount = error_count
                    self.errorok = False
                    errtoken = lookahead
                    if errtoken.type == '$end':
                        errtoken = None               # End of file!
                    if self.errorfunc:
                        if errtoken and not hasattr(errtoken, 'lexer'):
                            errtoken.lexer = lexer
                        self.state = state
                        tok = call_errorfunc(self.errorfunc, errtoken, self)
                        if self.errorok:
                            # User must have done some kind of panic
                            # mode recovery on their own.  The
                            # returned token is the next lookahead
                            lookahead = tok
                            errtoken = None
                            continue
                    else:
                        if errtoken:
                            if hasattr(errtoken, 'lineno'):
                                lineno = lookahead.lineno
                            else:
                                lineno = 0
                            if lineno:
                                sys.stderr.write('yacc: Syntax error at line %d, token=%s\n' % (lineno, errtoken.type))
                            else:
                                sys.stderr.write('yacc: Syntax error, token=%s' % errtoken.type)
                        else:
                            sys.stderr.write('yacc: Parse error in input. EOF\n')
                            return

                else:
                    errorcount = error_count

                # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
                # entire parse has been rolled back and we're completely hosed.   The token is
                # discarded and we just keep going.

                if len(statestack) <= 1 and lookahead.type != '$end':
                    lookahead = None
                    errtoken = None
                    state = 0
                    # Nuke the pushback stack
                    del lookaheadstack[:]
                    continue

                # case 2: the statestack has a couple of entries on it, but we're
                # at the end of the file. nuke the top entry and generate an error token

                # Start nuking entries on the stack
                if lookahead.type == '$end':
                    # Whoa. We're really hosed here. Bail out
                    return

                if lookahead.type != 'error':
                    sym = symstack[-1]
                    if sym.type == 'error':
                        # Hmmm. Error is on top of stack, we'll just nuke input
                        # symbol and continue
                        #--! TRACKING
                        if tracking:
                            sym.endlineno = getattr(lookahead, 'lineno', sym.lineno)
                            sym.endlexpos = getattr(lookahead, 'lexpos', sym.lexpos)
                        #--! TRACKING
                        lookahead = None
                        continue

                    # Create the error symbol for the first time and make it the new lookahead symbol
                    t = YaccSymbol()
                    t.type = 'error'

                    if hasattr(lookahead, 'lineno'):
                        t.lineno = t.endlineno = lookahead.lineno
                    if hasattr(lookahead, 'lexpos'):
                        t.lexpos = t.endlexpos = lookahead.lexpos
                    t.value = lookahead
                    lookaheadstack.append(lookahead)
                    lookahead = t
                else:
                    sym = symstack.pop()
                    #--! TRACKING
                    if tracking:
                        lookahead.lineno = sym.lineno
                        lookahead.lexpos = sym.lexpos
                    #--! TRACKING
                    statestack.pop()
                    state = statestack[-1]

                continue

            # Call an error function here
            raise RuntimeError('yacc: internal parser error!!!\n')

        #--! parsedebug-end

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # parseopt().
    #
    # Optimized version of parse() method.  DO NOT EDIT THIS CODE DIRECTLY!
    # This code is automatically generated by the ply/ygen.py script. Make
    # changes to the parsedebug() method instead.
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def parseopt(self, input=None, lexer=None, debug=False, tracking=False, tokenfunc=None):
        #--! parseopt-start
        lookahead = None                         # Current lookahead symbol
        lookaheadstack = []                      # Stack of lookahead symbols
        actions = self.action                    # Local reference to action table (to avoid lookup on self.)
        goto    = self.goto                      # Local reference to goto table (to avoid lookup on self.)
        prod    = self.productions               # Local reference to production list (to avoid lookup on self.)
        defaulted_states = self.defaulted_states # Local reference to defaulted states
        pslice  = YaccProduction(None)           # Production object passed to grammar rules
        errorcount = 0                           # Used during error recovery


        # If no lexer was given, we will try to use the lex module
        if not lexer:
            from . import lex
            lexer = lex.lexer

        # Set up the lexer and parser objects on pslice
        pslice.lexer = lexer
        pslice.parser = self

        # If input was supplied, pass to lexer
        if input is not None:
            lexer.input(input)

        if tokenfunc is None:
            # Tokenize function
            get_token = lexer.token
        else:
            get_token = tokenfunc

        # Set the parser() token method (sometimes used in error recovery)
        self.token = get_token

        # Set up the state and symbol stacks

        statestack = []                # Stack of parsing states
        self.statestack = statestack
        symstack   = []                # Stack of grammar symbols
        self.symstack = symstack

        pslice.stack = symstack         # Put in the production
        errtoken   = None               # Err token

        # The start state is assumed to be (0,$end)

        statestack.append(0)
        sym = YaccSymbol()
        sym.type = '$end'
        symstack.append(sym)
        state = 0
        while True:
            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer


            if state not in defaulted_states:
                if not lookahead:
                    if not lookaheadstack:
                        lookahead = get_token()     # Get the next token
                    else:
                        lookahead = lookaheadstack.pop()
                    if not lookahead:
                        lookahead = YaccSymbol()
                        lookahead.type = '$end'

                # Check the action table
                ltype = lookahead.type
                t = actions[state].get(ltype)
            else:
                t = defaulted_states[state]


            if t is not None:
                if t > 0:
                    # shift a symbol on the stack
                    statestack.append(t)
                    state = t


                    symstack.append(lookahead)
                    lookahead = None

                    # Decrease error count on successful shift
                    if errorcount:
                        errorcount -= 1
                    continue

                if t < 0:
                    # reduce a symbol on the stack, emit a production
                    p = prod[-t]
                    pname = p.name
                    plen  = p.len

                    # Get production function
                    sym = YaccSymbol()
                    sym.type = pname       # Production name
                    sym.value = None


                    if plen:
                        targ = symstack[-plen-1:]
                        targ[0] = sym

                        #--! TRACKING
                        if tracking:
                            t1 = targ[1]
                            sym.lineno = t1.lineno
                            sym.lexpos = t1.lexpos
                            t1 = targ[-1]
                            sym.endlineno = getattr(t1, 'endlineno', t1.lineno)
                            sym.endlexpos = getattr(t1, 'endlexpos', t1.lexpos)
                        #--! TRACKING

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated
                        # below as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            del symstack[-plen:]
                            self.state = state
                            p.callable(pslice)
                            del statestack[-plen:]
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)    # Save the current lookahead token
                            symstack.extend(targ[1:-1])         # Put the production slice back on the stack
                            statestack.pop()                    # Pop back one state (before the reduce)
                            state = statestack[-1]
                            sym.type = 'error'
                            sym.value = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = False

                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                    else:

                        #--! TRACKING
                        if tracking:
                            sym.lineno = lexer.lineno
                            sym.lexpos = lexer.lexpos
                        #--! TRACKING

                        targ = [sym]

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated
                        # above as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            self.state = state
                            p.callable(pslice)
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)    # Save the current lookahead token
                            statestack.pop()                    # Pop back one state (before the reduce)
                            state = statestack[-1]
                            sym.type = 'error'
                            sym.value = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = False

                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                if t == 0:
                    n = symstack[-1]
                    result = getattr(n, 'value', None)
                    return result

            if t is None:


                # We have some kind of parsing error here.  To handle
                # this, we are going to push the current token onto
                # the tokenstack and replace it with an 'error' token.
                # If there are any synchronization rules, they may
                # catch it.
                #
                # In addition to pushing the error token, we call call
                # the user defined p_error() function if this is the
                # first syntax error.  This function is only called if
                # errorcount == 0.
                if errorcount == 0 or self.errorok:
                    errorcount = error_count
                    self.errorok = False
                    errtoken = lookahead
                    if errtoken.type == '$end':
                        errtoken = None               # End of file!
                    if self.errorfunc:
                        if errtoken and not hasattr(errtoken, 'lexer'):
                            errtoken.lexer = lexer
                        self.state = state
                        tok = call_errorfunc(self.errorfunc, errtoken, self)
                        if self.errorok:
                            # User must have done some kind of panic
                            # mode recovery on their own.  The
                            # returned token is the next lookahead
                            lookahead = tok
                            errtoken = None
                            continue
                    else:
                        if errtoken:
                            if hasattr(errtoken, 'lineno'):
                                lineno = lookahead.lineno
                            else:
                                lineno = 0
                            if lineno:
                                sys.stderr.write('yacc: Syntax error at line %d, token=%s\n' % (lineno, errtoken.type))
                            else:
                                sys.stderr.write('yacc: Syntax error, token=%s' % errtoken.type)
                        else:
                            sys.stderr.write('yacc: Parse error in input. EOF\n')
                            return

                else:
                    errorcount = error_count

                # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
                # entire parse has been rolled back and we're completely hosed.   The token is
                # discarded and we just keep going.

                if len(statestack) <= 1 and lookahead.type != '$end':
                    lookahead = None
                    errtoken = None
                    state = 0
                    # Nuke the pushback stack
                    del lookaheadstack[:]
                    continue

                # case 2: the statestack has a couple of entries on it, but we're
                # at the end of the file. nuke the top entry and generate an error token

                # Start nuking entries on the stack
                if lookahead.type == '$end':
                    # Whoa. We're really hosed here. Bail out
                    return

                if lookahead.type != 'error':
                    sym = symstack[-1]
                    if sym.type == 'error':
                        # Hmmm. Error is on top of stack, we'll just nuke input
                        # symbol and continue
                        #--! TRACKING
                        if tracking:
                            sym.endlineno = getattr(lookahead, 'lineno', sym.lineno)
                            sym.endlexpos = getattr(lookahead, 'lexpos', sym.lexpos)
                        #--! TRACKING
                        lookahead = None
                        continue

                    # Create the error symbol for the first time and make it the new lookahead symbol
                    t = YaccSymbol()
                    t.type = 'error'

                    if hasattr(lookahead, 'lineno'):
                        t.lineno = t.endlineno = lookahead.lineno
                    if hasattr(lookahead, 'lexpos'):
                        t.lexpos = t.endlexpos = lookahead.lexpos
                    t.value = lookahead
                    lookaheadstack.append(lookahead)
                    lookahead = t
                else:
                    sym = symstack.pop()
                    #--! TRACKING
                    if tracking:
                        lookahead.lineno = sym.lineno
                        lookahead.lexpos = sym.lexpos
                    #--! TRACKING
                    statestack.pop()
                    state = statestack[-1]

                continue

            # Call an error function here
            raise RuntimeError('yacc: internal parser error!!!\n')

        #--! parseopt-end

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # parseopt_notrack().
    #
    # Optimized version of parseopt() with line number tracking removed.
    # DO NOT EDIT THIS CODE DIRECTLY. This code is automatically generated
    # by the ply/ygen.py script. Make changes to the parsedebug() method instead.
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def parseopt_notrack(self, input=None, lexer=None, debug=False, tracking=False, tokenfunc=None):
        #--! parseopt-notrack-start
        lookahead = None                         # Current lookahead symbol
        lookaheadstack = []                      # Stack of lookahead symbols
        actions = self.action                    # Local reference to action table (to avoid lookup on self.)
        goto    = self.goto                      # Local reference to goto table (to avoid lookup on self.)
        prod    = self.productions               # Local reference to production list (to avoid lookup on self.)
        defaulted_states = self.defaulted_states # Local reference to defaulted states
        pslice  = YaccProduction(None)           # Production object passed to grammar rules
        errorcount = 0                           # Used during error recovery


        # If no lexer was given, we will try to use the lex module
        if not lexer:
            from . import lex
            lexer = lex.lexer

        # Set up the lexer and parser objects on pslice
        pslice.lexer = lexer
        pslice.parser = self

        # If input was supplied, pass to lexer
        if input is not None:
            lexer.input(input)

        if tokenfunc is None:
            # Tokenize function
            get_token = lexer.token
        else:
            get_token = tokenfunc

        # Set the parser() token method (sometimes used in error recovery)
        self.token = get_token

        # Set up the state and symbol stacks

        statestack = []                # Stack of parsing states
        self.statestack = statestack
        symstack   = []                # Stack of grammar symbols
        self.symstack = symstack

        pslice.stack = symstack         # Put in the production
        errtoken   = None               # Err token

        # The start state is assumed to be (0,$end)

        statestack.append(0)
        sym = YaccSymbol()
        sym.type = '$end'
        symstack.append(sym)
        state = 0
        while True:
            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer


            if state not in defaulted_states:
                if not lookahead:
                    if not lookaheadstack:
                        lookahead = get_token()     # Get the next token
                    else:
                        lookahead = lookaheadstack.pop()
                    if not lookahead:
                        lookahead = YaccSymbol()
                        lookahead.type = '$end'

                # Check the action table
                ltype = lookahead.type
                t = actions[state].get(ltype)
            else:
                t = defaulted_states[state]


            if t is not None:
                if t > 0:
                    # shift a symbol on the stack
                    statestack.append(t)
                    state = t


                    symstack.append(lookahead)
                    lookahead = None

                    # Decrease error count on successful shift
                    if errorcount:
                        errorcount -= 1
                    continue

                if t < 0:
                    # reduce a symbol on the stack, emit a production
                    p = prod[-t]
                    pname = p.name
                    plen  = p.len

                    # Get production function
                    sym = YaccSymbol()
                    sym.type = pname       # Production name
                    sym.value = None


                    if plen:
                        targ = symstack[-plen-1:]
                        targ[0] = sym


                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated
                        # below as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            del symstack[-plen:]
                            self.state = state
                            p.callable(pslice)
                            del statestack[-plen:]
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)    # Save the current lookahead token
                            symstack.extend(targ[1:-1])         # Put the production slice back on the stack
                            statestack.pop()                    # Pop back one state (before the reduce)
                            state = statestack[-1]
                            sym.type = 'error'
                            sym.value = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = False

                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                    else:


                        targ = [sym]

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated
                        # above as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            self.state = state
                            p.callable(pslice)
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)    # Save the current lookahead token
                            statestack.pop()                    # Pop back one state (before the reduce)
                            state = statestack[-1]
                            sym.type = 'error'
                            sym.value = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = False

                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                if t == 0:
                    n = symstack[-1]
                    result = getattr(n, 'value', None)
                    return result

            if t is None:


                # We have some kind of parsing error here.  To handle
                # this, we are going to push the current token onto
                # the tokenstack and replace it with an 'error' token.
                # If there are any synchronization rules, they may
                # catch it.
                #
                # In addition to pushing the error token, we call call
                # the user defined p_error() function if this is the
                # first syntax error.  This function is only called if
                # errorcount == 0.
                if errorcount == 0 or self.errorok:
                    errorcount = error_count
                    self.errorok = False
                    errtoken = lookahead
                    if errtoken.type == '$end':
                        errtoken = None               # End of file!
                    if self.errorfunc:
                        if errtoken and not hasattr(errtoken, 'lexer'):
                            errtoken.lexer = lexer
                        self.state = state
                        tok = call_errorfunc(self.errorfunc, errtoken, self)
                        if self.errorok:
                            # User must have done some kind of panic
                            # mode recovery on their own.  The
                            # returned token is the next lookahead
                            lookahead = tok
                            errtoken = None
                            continue
                    else:
                        if errtoken:
                            if hasattr(errtoken, 'lineno'):
                                lineno = lookahead.lineno
                            else:
                                lineno = 0
                            if lineno:
                                sys.stderr.write('yacc: Syntax error at line %d, token=%s\n' % (lineno, errtoken.type))
                            else:
                                sys.stderr.write('yacc: Syntax error, token=%s' % errtoken.type)
                        else:
                            sys.stderr.write('yacc: Parse error in input. EOF\n')
                            return

                else:
                    errorcount = error_count

                # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
                # entire parse has been rolled back and we're completely hosed.   The token is
                # discarded and we just keep going.

                if len(statestack) <= 1 and lookahead.type != '$end':
                    lookahead = None
                    errtoken = None
                    state = 0
                    # Nuke the pushback stack
                    del lookaheadstack[:]
                    continue

                # case 2: the statestack has a couple of entries on it, but we're
                # at the end of the file. nuke the top entry and generate an error token

                # Start nuking entries on the stack
                if lookahead.type == '$end':
                    # Whoa. We're really hosed here. Bail out
                    return

                if lookahead.type != 'error':
                    sym = symstack[-1]
                    if sym.type == 'error':
                        # Hmmm. Error is on top of stack, we'll just nuke input
                        # symbol and continue
                        lookahead = None
                        continue

                    # Create the error symbol for the first time and make it the new lookahead symbol
                    t = YaccSymbol()
                    t.type = 'error'

                    if hasattr(lookahead, 'lineno'):
                        t.lineno = t.endlineno = lookahead.lineno
                    if hasattr(lookahead, 'lexpos'):
                        t.lexpos = t.endlexpos = lookahead.lexpos
                    t.value = lookahead
                    lookaheadstack.append(lookahead)
                    lookahead = t
                else:
                    sym = symstack.pop()
                    statestack.pop()
                    state = statestack[-1]

                continue

            # Call an error function here
            raise RuntimeError('yacc: internal parser error!!!\n')

        #--! parseopt-notrack-end

# -----------------------------------------------------------------------------
#                          === Grammar Representation ===
#
# The following functions, classes, and variables are used to represent and
# manipulate the rules that make up a grammar.
# -----------------------------------------------------------------------------

# regex matching identifiers
_is_identifier = re.compile(r'^[a-zA-Z0-9_-]+$')

# -----------------------------------------------------------------------------
# class Production:
#
# This class stores the raw information about a single production or grammar rule.
# A grammar rule refers to a specification such as this:
#
#       expr : expr PLUS term
#
# Here are the basic attributes defined on all productions
#
#       name     - Name of the production.  For example 'expr'
#       prod     - A list of symbols on the right side ['expr','PLUS','term']
#       prec     - Production precedence level
#       number   - Production number.
#       func     - Function that executes on reduce
#       file     - File where production function is defined
#       lineno   - Line number where production function is defined
#
# The following attributes are defined or optional.
#
#       len       - Length of the production (number of symbols on right hand side)
#       usyms     - Set of unique symbols found in the production
# -----------------------------------------------------------------------------

class Production(object):
    reduced = 0
    def __init__(self, number, name, prod, precedence=('right', 0), func=None, file='', line=0):
        self.name     = name
        self.prod     = tuple(prod)
        self.number   = number
        self.func     = func
        self.callable = None
        self.file     = file
        self.line     = line
        self.prec     = precedence

        # Internal settings used during table construction

        self.len  = len(self.prod)   # Length of the production

        # Create a list of unique production symbols used in the production
        self.usyms = []
        for s in self.prod:
            if s not in self.usyms:
                self.usyms.append(s)

        # List of all LR items for the production
        self.lr_items = []
        self.lr_next = None

        # Create a string representation
        if self.prod:
            self.str = '%s -> %s' % (self.name, ' '.join(self.prod))
        else:
            self.str = '%s -> <empty>' % self.name

    def __str__(self):
        return self.str

    def __repr__(self):
        return 'Production(' + str(self) + ')'

    def __len__(self):
        return len(self.prod)

    def __nonzero__(self):
        return 1

    def __getitem__(self, index):
        return self.prod[index]

    # Return the nth lr_item from the production (or None if at the end)
    def lr_item(self, n):
        if n > len(self.prod):
            return None
        p = LRItem(self, n)
        # Precompute the list of productions immediately following.
        try:
            p.lr_after = Prodnames[p.prod[n+1]]
        except (IndexError, KeyError):
            p.lr_after = []
        try:
            p.lr_before = p.prod[n-1]
        except IndexError:
            p.lr_before = None
        return p

    # Bind the production function name to a callable
    def bind(self, pdict):
        if self.func:
            self.callable = pdict[self.func]

# This class serves as a minimal standin for Production objects when
# reading table data from files.   It only contains information
# actually used by the LR parsing engine, plus some additional
# debugging information.
class MiniProduction(object):
    def __init__(self, str, name, len, func, file, line):
        self.name     = name
        self.len      = len
        self.func     = func
        self.callable = None
        self.file     = file
        self.line     = line
        self.str      = str

    def __str__(self):
        return self.str

    def __repr__(self):
        return 'MiniProduction(%s)' % self.str

    # Bind the production function name to a callable
    def bind(self, pdict):
        if self.func:
            self.callable = pdict[self.func]


# -----------------------------------------------------------------------------
# class LRItem
#
# This class represents a specific stage of parsing a production rule.  For
# example:
#
#       expr : expr . PLUS term
#
# In the above, the "." represents the current location of the parse.  Here
# basic attributes:
#
#       name       - Name of the production.  For example 'expr'
#       prod       - A list of symbols on the right side ['expr','.', 'PLUS','term']
#       number     - Production number.
#
#       lr_next      Next LR item. Example, if we are ' expr -> expr . PLUS term'
#                    then lr_next refers to 'expr -> expr PLUS . term'
#       lr_index   - LR item index (location of the ".") in the prod list.
#       lookaheads - LALR lookahead symbols for this item
#       len        - Length of the production (number of symbols on right hand side)
#       lr_after    - List of all productions that immediately follow
#       lr_before   - Grammar symbol immediately before
# -----------------------------------------------------------------------------

class LRItem(object):
    def __init__(self, p, n):
        self.name       = p.name
        self.prod       = list(p.prod)
        self.number     = p.number
        self.lr_index   = n
        self.lookaheads = {}
        self.prod.insert(n, '.')
        self.prod       = tuple(self.prod)
        self.len        = len(self.prod)
        self.usyms      = p.usyms

    def __str__(self):
        if self.prod:
            s = '%s -> %s' % (self.name, ' '.join(self.prod))
        else:
            s = '%s -> <empty>' % self.name
        return s

    def __repr__(self):
        return 'LRItem(' + str(self) + ')'

# -----------------------------------------------------------------------------
# rightmost_terminal()
#
# Return the rightmost terminal from a list of symbols.  Used in add_production()
# -----------------------------------------------------------------------------
def rightmost_terminal(symbols, terminals):
    i = len(symbols) - 1
    while i >= 0:
        if symbols[i] in terminals:
            return symbols[i]
        i -= 1
    return None

# -----------------------------------------------------------------------------
#                           === GRAMMAR CLASS ===
#
# The following class represents the contents of the specified grammar along
# with various computed properties such as first sets, follow sets, LR items, etc.
# This data is used for critical parts of the table generation process later.
# -----------------------------------------------------------------------------

class GrammarError(YaccError):
    pass

class Grammar(object):
    def __init__(self, terminals):
        self.Productions  = [None]  # A list of all of the productions.  The first
                                    # entry is always reserved for the purpose of
                                    # building an augmented grammar

        self.Prodnames    = {}      # A dictionary mapping the names of nonterminals to a list of all
                                    # productions of that nonterminal.

        self.Prodmap      = {}      # A dictionary that is only used to detect duplicate
                                    # productions.

        self.Terminals    = {}      # A dictionary mapping the names of terminal symbols to a
                                    # list of the rules where they are used.

        for term in terminals:
            self.Terminals[term] = []

        self.Terminals['error'] = []

        self.Nonterminals = {}      # A dictionary mapping names of nonterminals to a list
                                    # of rule numbers where they are used.

        self.First        = {}      # A dictionary of precomputed FIRST(x) symbols

        self.Follow       = {}      # A dictionary of precomputed FOLLOW(x) symbols

        self.Precedence   = {}      # Precedence rules for each terminal. Contains tuples of the
                                    # form ('right',level) or ('nonassoc', level) or ('left',level)

        self.UsedPrecedence = set() # Precedence rules that were actually used by the grammer.
                                    # This is only used to provide error checking and to generate
                                    # a warning about unused precedence rules.

        self.Start = None           # Starting symbol for the grammar


    def __len__(self):
        return len(self.Productions)

    def __getitem__(self, index):
        return self.Productions[index]

    # -----------------------------------------------------------------------------
    # set_precedence()
    #
    # Sets the precedence for a given terminal. assoc is the associativity such as
    # 'left','right', or 'nonassoc'.  level is a numeric level.
    #
    # -----------------------------------------------------------------------------

    def set_precedence(self, term, assoc, level):
        assert self.Productions == [None], 'Must call set_precedence() before add_production()'
        if term in self.Precedence:
            raise GrammarError('Precedence already specified for terminal %r' % term)
        if assoc not in ['left', 'right', 'nonassoc']:
            raise GrammarError("Associativity must be one of 'left','right', or 'nonassoc'")
        self.Precedence[term] = (assoc, level)

    # -----------------------------------------------------------------------------
    # add_production()
    #
    # Given an action function, this function assembles a production rule and
    # computes its precedence level.
    #
    # The production rule is supplied as a list of symbols.   For example,
    # a rule such as 'expr : expr PLUS term' has a production name of 'expr' and
    # symbols ['expr','PLUS','term'].
    #
    # Precedence is determined by the precedence of the right-most non-terminal
    # or the precedence of a terminal specified by %prec.
    #
    # A variety of error checks are performed to make sure production symbols
    # are valid and that %prec is used correctly.
    # -----------------------------------------------------------------------------

    def add_production(self, prodname, syms, func=None, file='', line=0):

        if prodname in self.Terminals:
            raise GrammarError('%s:%d: Illegal rule name %r. Already defined as a token' % (file, line, prodname))
        if prodname == 'error':
            raise GrammarError('%s:%d: Illegal rule name %r. error is a reserved word' % (file, line, prodname))
        if not _is_identifier.match(prodname):
            raise GrammarError('%s:%d: Illegal rule name %r' % (file, line, prodname))

        # Look for literal tokens
        for n, s in enumerate(syms):
            if s[0] in "'\"":
                try:
                    c = eval(s)
                    if (len(c) > 1):
                        raise GrammarError('%s:%d: Literal token %s in rule %r may only be a single character' %
                                           (file, line, s, prodname))
                    if c not in self.Terminals:
                        self.Terminals[c] = []
                    syms[n] = c
                    continue
                except SyntaxError:
                    pass
            if not _is_identifier.match(s) and s != '%prec':
                raise GrammarError('%s:%d: Illegal name %r in rule %r' % (file, line, s, prodname))

        # Determine the precedence level
        if '%prec' in syms:
            if syms[-1] == '%prec':
                raise GrammarError('%s:%d: Syntax error. Nothing follows %%prec' % (file, line))
            if syms[-2] != '%prec':
                raise GrammarError('%s:%d: Syntax error. %%prec can only appear at the end of a grammar rule' %
                                   (file, line))
            precname = syms[-1]
            prodprec = self.Precedence.get(precname)
            if not prodprec:
                raise GrammarError('%s:%d: Nothing known about the precedence of %r' % (file, line, precname))
            else:
                self.UsedPrecedence.add(precname)
            del syms[-2:]     # Drop %prec from the rule
        else:
            # If no %prec, precedence is determined by the rightmost terminal symbol
            precname = rightmost_terminal(syms, self.Terminals)
            prodprec = self.Precedence.get(precname, ('right', 0))

        # See if the rule is already in the rulemap
        map = '%s -> %s' % (prodname, syms)
        if map in self.Prodmap:
            m = self.Prodmap[map]
            raise GrammarError('%s:%d: Duplicate rule %s. ' % (file, line, m) +
                               'Previous definition at %s:%d' % (m.file, m.line))

        # From this point on, everything is valid.  Create a new Production instance
        pnumber  = len(self.Productions)
        if prodname not in self.Nonterminals:
            self.Nonterminals[prodname] = []

        # Add the production number to Terminals and Nonterminals
        for t in syms:
            if t in self.Terminals:
                self.Terminals[t].append(pnumber)
            else:
                if t not in self.Nonterminals:
                    self.Nonterminals[t] = []
                self.Nonterminals[t].append(pnumber)

        # Create a production and add it to the list of productions
        p = Production(pnumber, prodname, syms, prodprec, func, file, line)
        self.Productions.append(p)
        self.Prodmap[map] = p

        # Add to the global productions list
        try:
            self.Prodnames[prodname].append(p)
        except KeyError:
            self.Prodnames[prodname] = [p]

    # -----------------------------------------------------------------------------
    # set_start()
    #
    # Sets the starting symbol and creates the augmented grammar.  Production
    # rule 0 is S' -> start where start is the start symbol.
    # -----------------------------------------------------------------------------

    def set_start(self, start=None):
        if not start:
            start = self.Productions[1].name
        if start not in self.Nonterminals:
            raise GrammarError('start symbol %s undefined' % start)
        self.Productions[0] = Production(0, "S'", [start])
        self.Nonterminals[start].append(0)
        self.Start = start

    # -----------------------------------------------------------------------------
    # find_unreachable()
    #
    # Find all of the nonterminal symbols that can't be reached from the starting
    # symbol.  Returns a list of nonterminals that can't be reached.
    # -----------------------------------------------------------------------------

    def find_unreachable(self):

        # Mark all symbols that are reachable from a symbol s
        def mark_reachable_from(s):
            if s in reachable:
                return
            reachable.add(s)
            for p in self.Prodnames.get(s, []):
                for r in p.prod:
                    mark_reachable_from(r)

        reachable = set()
        mark_reachable_from(self.Productions[0].prod[0])
        return [s for s in self.Nonterminals if s not in reachable]

    # -----------------------------------------------------------------------------
    # infinite_cycles()
    #
    # This function looks at the various parsing rules and tries to detect
    # infinite recursion cycles (grammar rules where there is no possible way
    # to derive a string of only terminals).
    # -----------------------------------------------------------------------------

    def infinite_cycles(self):
        terminates = {}

        # Terminals:
        for t in self.Terminals:
            terminates[t] = True

        terminates['$end'] = True

        # Nonterminals:

        # Initialize to false:
        for n in self.Nonterminals:
            terminates[n] = False

        # Then propagate termination until no change:
        while True:
            some_change = False
            for (n, pl) in self.Prodnames.items():
                # Nonterminal n terminates iff any of its productions terminates.
                for p in pl:
                    # Production p terminates iff all of its rhs symbols terminate.
                    for s in p.prod:
                        if not terminates[s]:
                            # The symbol s does not terminate,
                            # so production p does not terminate.
                            p_terminates = False
                            break
                    else:
                        # didn't break from the loop,
                        # so every symbol s terminates
                        # so production p terminates.
                        p_terminates = True

                    if p_terminates:
                        # symbol n terminates!
                        if not terminates[n]:
                            terminates[n] = True
                            some_change = True
                        # Don't need to consider any more productions for this n.
                        break

            if not some_change:
                break

        infinite = []
        for (s, term) in terminates.items():
            if not term:
                if s not in self.Prodnames and s not in self.Terminals and s != 'error':
                    # s is used-but-not-defined, and we've already warned of that,
                    # so it would be overkill to say that it's also non-terminating.
                    pass
                else:
                    infinite.append(s)

        return infinite

    # -----------------------------------------------------------------------------
    # undefined_symbols()
    #
    # Find all symbols that were used the grammar, but not defined as tokens or
    # grammar rules.  Returns a list of tuples (sym, prod) where sym in the symbol
    # and prod is the production where the symbol was used.
    # -----------------------------------------------------------------------------
    def undefined_symbols(self):
        result = []
        for p in self.Productions:
            if not p:
                continue

            for s in p.prod:
                if s not in self.Prodnames and s not in self.Terminals and s != 'error':
                    result.append((s, p))
        return result

    # -----------------------------------------------------------------------------
    # unused_terminals()
    #
    # Find all terminals that were defined, but not used by the grammar.  Returns
    # a list of all symbols.
    # -----------------------------------------------------------------------------
    def unused_terminals(self):
        unused_tok = []
        for s, v in self.Terminals.items():
            if s != 'error' and not v:
                unused_tok.append(s)

        return unused_tok

    # ------------------------------------------------------------------------------
    # unused_rules()
    #
    # Find all grammar rules that were defined,  but not used (maybe not reachable)
    # Returns a list of productions.
    # ------------------------------------------------------------------------------

    def unused_rules(self):
        unused_prod = []
        for s, v in self.Nonterminals.items():
            if not v:
                p = self.Prodnames[s][0]
                unused_prod.append(p)
        return unused_prod

    # -----------------------------------------------------------------------------
    # unused_precedence()
    #
    # Returns a list of tuples (term,precedence) corresponding to precedence
    # rules that were never used by the grammar.  term is the name of the terminal
    # on which precedence was applied and precedence is a string such as 'left' or
    # 'right' corresponding to the type of precedence.
    # -----------------------------------------------------------------------------

    def unused_precedence(self):
        unused = []
        for termname in self.Precedence:
            if not (termname in self.Terminals or termname in self.UsedPrecedence):
                unused.append((termname, self.Precedence[termname][0]))

        return unused

    # -------------------------------------------------------------------------
    # _first()
    #
    # Compute the value of FIRST1(beta) where beta is a tuple of symbols.
    #
    # During execution of compute_first1, the result may be incomplete.
    # Afterward (e.g., when called from compute_follow()), it will be complete.
    # -------------------------------------------------------------------------
    def _first(self, beta):

        # We are computing First(x1,x2,x3,...,xn)
        result = []
        for x in beta:
            x_produces_empty = False

            # Add all the non-<empty> symbols of First[x] to the result.
            for f in self.First[x]:
                if f == '<empty>':
                    x_produces_empty = True
                else:
                    if f not in result:
                        result.append(f)

            if x_produces_empty:
                # We have to consider the next x in beta,
                # i.e. stay in the loop.
                pass
            else:
                # We don't have to consider any further symbols in beta.
                break
        else:
            # There was no 'break' from the loop,
            # so x_produces_empty was true for all x in beta,
            # so beta produces empty as well.
            result.append('<empty>')

        return result

    # -------------------------------------------------------------------------
    # compute_first()
    #
    # Compute the value of FIRST1(X) for all symbols
    # -------------------------------------------------------------------------
    def compute_first(self):
        if self.First:
            return self.First

        # Terminals:
        for t in self.Terminals:
            self.First[t] = [t]

        self.First['$end'] = ['$end']

        # Nonterminals:

        # Initialize to the empty set:
        for n in self.Nonterminals:
            self.First[n] = []

        # Then propagate symbols until no change:
        while True:
            some_change = False
            for n in self.Nonterminals:
                for p in self.Prodnames[n]:
                    for f in self._first(p.prod):
                        if f not in self.First[n]:
                            self.First[n].append(f)
                            some_change = True
            if not some_change:
                break

        return self.First

    # ---------------------------------------------------------------------
    # compute_follow()
    #
    # Computes all of the follow sets for every non-terminal symbol.  The
    # follow set is the set of all symbols that might follow a given
    # non-terminal.  See the Dragon book, 2nd Ed. p. 189.
    # ---------------------------------------------------------------------
    def compute_follow(self, start=None):
        # If already computed, return the result
        if self.Follow:
            return self.Follow

        # If first sets not computed yet, do that first.
        if not self.First:
            self.compute_first()

        # Add '$end' to the follow list of the start symbol
        for k in self.Nonterminals:
            self.Follow[k] = []

        if not start:
            start = self.Productions[1].name

        self.Follow[start] = ['$end']

        while True:
            didadd = False
            for p in self.Productions[1:]:
                # Here is the production set
                for i, B in enumerate(p.prod):
                    if B in self.Nonterminals:
                        # Okay. We got a non-terminal in a production
                        fst = self._first(p.prod[i+1:])
                        hasempty = False
                        for f in fst:
                            if f != '<empty>' and f not in self.Follow[B]:
                                self.Follow[B].append(f)
                                didadd = True
                            if f == '<empty>':
                                hasempty = True
                        if hasempty or i == (len(p.prod)-1):
                            # Add elements of follow(a) to follow(b)
                            for f in self.Follow[p.name]:
                                if f not in self.Follow[B]:
                                    self.Follow[B].append(f)
                                    didadd = True
            if not didadd:
                break
        return self.Follow


    # -----------------------------------------------------------------------------
    # build_lritems()
    #
    # This function walks the list of productions and builds a complete set of the
    # LR items.  The LR items are stored in two ways:  First, they are uniquely
    # numbered and placed in the list _lritems.  Second, a linked list of LR items
    # is built for each production.  For example:
    #
    #   E -> E PLUS E
    #
    # Creates the list
    #
    #  [E -> . E PLUS E, E -> E . PLUS E, E -> E PLUS . E, E -> E PLUS E . ]
    # -----------------------------------------------------------------------------

    def build_lritems(self):
        for p in self.Productions:
            lastlri = p
            i = 0
            lr_items = []
            while True:
                if i > len(p):
                    lri = None
                else:
                    lri = LRItem(p, i)
                    # Precompute the list of productions immediately following
                    try:
                        lri.lr_after = self.Prodnames[lri.prod[i+1]]
                    except (IndexError, KeyError):
                        lri.lr_after = []
                    try:
                        lri.lr_before = lri.prod[i-1]
                    except IndexError:
                        lri.lr_before = None

                lastlri.lr_next = lri
                if not lri:
                    break
                lr_items.append(lri)
                lastlri = lri
                i += 1
            p.lr_items = lr_items

# -----------------------------------------------------------------------------
#                            == Class LRTable ==
#
# This basic class represents a basic table of LR parsing information.
# Methods for generating the tables are not defined here.  They are defined
# in the derived class LRGeneratedTable.
# -----------------------------------------------------------------------------

class VersionError(YaccError):
    pass

class LRTable(object):
    def __init__(self):
        self.lr_action = None
        self.lr_goto = None
        self.lr_productions = None
        self.lr_method = None

    def read_table(self, module):
        if isinstance(module, types.ModuleType):
            parsetab = module
        else:
            exec('import %s' % module)
            parsetab = sys.modules[module]

        if parsetab._tabversion != __tabversion__:
            raise VersionError('yacc table file version is out of date')

        self.lr_action = parsetab._lr_action
        self.lr_goto = parsetab._lr_goto

        self.lr_productions = []
        for p in parsetab._lr_productions:
            self.lr_productions.append(MiniProduction(*p))

        self.lr_method = parsetab._lr_method
        return parsetab._lr_signature

    def read_pickle(self, filename):
        try:
            import cPickle as pickle
        except ImportError:
            import pickle

        if not os.path.exists(filename):
          raise ImportError

        in_f = open(filename, 'rb')

        tabversion = pickle.load(in_f)
        if tabversion != __tabversion__:
            raise VersionError('yacc table file version is out of date')
        self.lr_method = pickle.load(in_f)
        signature      = pickle.load(in_f)
        self.lr_action = pickle.load(in_f)
        self.lr_goto   = pickle.load(in_f)
        productions    = pickle.load(in_f)

        self.lr_productions = []
        for p in productions:
            self.lr_productions.append(MiniProduction(*p))

        in_f.close()
        return signature

    # Bind all production function names to callable objects in pdict
    def bind_callables(self, pdict):
        for p in self.lr_productions:
            p.bind(pdict)


# -----------------------------------------------------------------------------
#                           === LR Generator ===
#
# The following classes and functions are used to generate LR parsing tables on
# a grammar.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# digraph()
# traverse()
#
# The following two functions are used to compute set valued functions
# of the form:
#
#     F(x) = F'(x) U U{F(y) | x R y}
#
# This is used to compute the values of Read() sets as well as FOLLOW sets
# in LALR(1) generation.
#
# Inputs:  X    - An input set
#          R    - A relation
#          FP   - Set-valued function
# ------------------------------------------------------------------------------

def digraph(X, R, FP):
    N = {}
    for x in X:
        N[x] = 0
    stack = []
    F = {}
    for x in X:
        if N[x] == 0:
            traverse(x, N, stack, F, X, R, FP)
    return F

def traverse(x, N, stack, F, X, R, FP):
    stack.append(x)
    d = len(stack)
    N[x] = d
    F[x] = FP(x)             # F(X) <- F'(x)

    rel = R(x)               # Get y's related to x
    for y in rel:
        if N[y] == 0:
            traverse(y, N, stack, F, X, R, FP)
        N[x] = min(N[x], N[y])
        for a in F.get(y, []):
            if a not in F[x]:
                F[x].append(a)
    if N[x] == d:
        N[stack[-1]] = MAXINT
        F[stack[-1]] = F[x]
        element = stack.pop()
        while element != x:
            N[stack[-1]] = MAXINT
            F[stack[-1]] = F[x]
            element = stack.pop()

class LALRError(YaccError):
    pass

# -----------------------------------------------------------------------------
#                             == LRGeneratedTable ==
#
# This class implements the LR table generation algorithm.  There are no
# public methods except for write()
# -----------------------------------------------------------------------------

class LRGeneratedTable(LRTable):
    def __init__(self, grammar, method='LALR', log=None):
        if method not in ['SLR', 'LALR']:
            raise LALRError('Unsupported method %s' % method)

        self.grammar = grammar
        self.lr_method = method

        # Set up the logger
        if not log:
            log = NullLogger()
        self.log = log

        # Internal attributes
        self.lr_action     = {}        # Action table
        self.lr_goto       = {}        # Goto table
        self.lr_productions  = grammar.Productions    # Copy of grammar Production array
        self.lr_goto_cache = {}        # Cache of computed gotos
        self.lr0_cidhash   = {}        # Cache of closures

        self._add_count    = 0         # Internal counter used to detect cycles

        # Diagonistic information filled in by the table generator
        self.sr_conflict   = 0
        self.rr_conflict   = 0
        self.conflicts     = []        # List of conflicts

        self.sr_conflicts  = []
        self.rr_conflicts  = []

        # Build the tables
        self.grammar.build_lritems()
        self.grammar.compute_first()
        self.grammar.compute_follow()
        self.lr_parse_table()

    # Compute the LR(0) closure operation on I, where I is a set of LR(0) items.

    def lr0_closure(self, I):
        self._add_count += 1

        # Add everything in I to J
        J = I[:]
        didadd = True
        while didadd:
            didadd = False
            for j in J:
                for x in j.lr_after:
                    if getattr(x, 'lr0_added', 0) == self._add_count:
                        continue
                    # Add B --> .G to J
                    J.append(x.lr_next)
                    x.lr0_added = self._add_count
                    didadd = True

        return J

    # Compute the LR(0) goto function goto(I,X) where I is a set
    # of LR(0) items and X is a grammar symbol.   This function is written
    # in a way that guarantees uniqueness of the generated goto sets
    # (i.e. the same goto set will never be returned as two different Python
    # objects).  With uniqueness, we can later do fast set comparisons using
    # id(obj) instead of element-wise comparison.

    def lr0_goto(self, I, x):
        # First we look for a previously cached entry
        g = self.lr_goto_cache.get((id(I), x))
        if g:
            return g

        # Now we generate the goto set in a way that guarantees uniqueness
        # of the result

        s = self.lr_goto_cache.get(x)
        if not s:
            s = {}
            self.lr_goto_cache[x] = s

        gs = []
        for p in I:
            n = p.lr_next
            if n and n.lr_before == x:
                s1 = s.get(id(n))
                if not s1:
                    s1 = {}
                    s[id(n)] = s1
                gs.append(n)
                s = s1
        g = s.get('$end')
        if not g:
            if gs:
                g = self.lr0_closure(gs)
                s['$end'] = g
            else:
                s['$end'] = gs
        self.lr_goto_cache[(id(I), x)] = g
        return g

    # Compute the LR(0) sets of item function
    def lr0_items(self):
        C = [self.lr0_closure([self.grammar.Productions[0].lr_next])]
        i = 0
        for I in C:
            self.lr0_cidhash[id(I)] = i
            i += 1

        # Loop over the items in C and each grammar symbols
        i = 0
        while i < len(C):
            I = C[i]
            i += 1

            # Collect all of the symbols that could possibly be in the goto(I,X) sets
            asyms = {}
            for ii in I:
                for s in ii.usyms:
                    asyms[s] = None

            for x in asyms:
                g = self.lr0_goto(I, x)
                if not g or id(g) in self.lr0_cidhash:
                    continue
                self.lr0_cidhash[id(g)] = len(C)
                C.append(g)

        return C

    # -----------------------------------------------------------------------------
    #                       ==== LALR(1) Parsing ====
    #
    # LALR(1) parsing is almost exactly the same as SLR except that instead of
    # relying upon Follow() sets when performing reductions, a more selective
    # lookahead set that incorporates the state of the LR(0) machine is utilized.
    # Thus, we mainly just have to focus on calculating the lookahead sets.
    #
    # The method used here is due to DeRemer and Pennelo (1982).
    #
    # DeRemer, F. L., and T. J. Pennelo: "Efficient Computation of LALR(1)
    #     Lookahead Sets", ACM Transactions on Programming Languages and Systems,
    #     Vol. 4, No. 4, Oct. 1982, pp. 615-649
    #
    # Further details can also be found in:
    #
    #  J. Tremblay and P. Sorenson, "The Theory and Practice of Compiler Writing",
    #      McGraw-Hill Book Company, (1985).
    #
    # -----------------------------------------------------------------------------

    # -----------------------------------------------------------------------------
    # compute_nullable_nonterminals()
    #
    # Creates a dictionary containing all of the non-terminals that might produce
    # an empty production.
    # -----------------------------------------------------------------------------

    def compute_nullable_nonterminals(self):
        nullable = set()
        num_nullable = 0
        while True:
            for p in self.grammar.Productions[1:]:
                if p.len == 0:
                    nullable.add(p.name)
                    continue
                for t in p.prod:
                    if t not in nullable:
                        break
                else:
                    nullable.add(p.name)
            if len(nullable) == num_nullable:
                break
            num_nullable = len(nullable)
        return nullable

    # -----------------------------------------------------------------------------
    # find_nonterminal_trans(C)
    #
    # Given a set of LR(0) items, this functions finds all of the non-terminal
    # transitions.    These are transitions in which a dot appears immediately before
    # a non-terminal.   Returns a list of tuples of the form (state,N) where state
    # is the state number and N is the nonterminal symbol.
    #
    # The input C is the set of LR(0) items.
    # -----------------------------------------------------------------------------

    def find_nonterminal_transitions(self, C):
        trans = []
        for stateno, state in enumerate(C):
            for p in state:
                if p.lr_index < p.len - 1:
                    t = (stateno, p.prod[p.lr_index+1])
                    if t[1] in self.grammar.Nonterminals:
                        if t not in trans:
                            trans.append(t)
        return trans

    # -----------------------------------------------------------------------------
    # dr_relation()
    #
    # Computes the DR(p,A) relationships for non-terminal transitions.  The input
    # is a tuple (state,N) where state is a number and N is a nonterminal symbol.
    #
    # Returns a list of terminals.
    # -----------------------------------------------------------------------------

    def dr_relation(self, C, trans, nullable):
        dr_set = {}
        state, N = trans
        terms = []

        g = self.lr0_goto(C[state], N)
        for p in g:
            if p.lr_index < p.len - 1:
                a = p.prod[p.lr_index+1]
                if a in self.grammar.Terminals:
                    if a not in terms:
                        terms.append(a)

        # This extra bit is to handle the start state
        if state == 0 and N == self.grammar.Productions[0].prod[0]:
            terms.append('$end')

        return terms

    # -----------------------------------------------------------------------------
    # reads_relation()
    #
    # Computes the READS() relation (p,A) READS (t,C).
    # -----------------------------------------------------------------------------

    def reads_relation(self, C, trans, empty):
        # Look for empty transitions
        rel = []
        state, N = trans

        g = self.lr0_goto(C[state], N)
        j = self.lr0_cidhash.get(id(g), -1)
        for p in g:
            if p.lr_index < p.len - 1:
                a = p.prod[p.lr_index + 1]
                if a in empty:
                    rel.append((j, a))

        return rel

    # -----------------------------------------------------------------------------
    # compute_lookback_includes()
    #
    # Determines the lookback and includes relations
    #
    # LOOKBACK:
    #
    # This relation is determined by running the LR(0) state machine forward.
    # For example, starting with a production "N : . A B C", we run it forward
    # to obtain "N : A B C ."   We then build a relationship between this final
    # state and the starting state.   These relationships are stored in a dictionary
    # lookdict.
    #
    # INCLUDES:
    #
    # Computes the INCLUDE() relation (p,A) INCLUDES (p',B).
    #
    # This relation is used to determine non-terminal transitions that occur
    # inside of other non-terminal transition states.   (p,A) INCLUDES (p', B)
    # if the following holds:
    #
    #       B -> LAT, where T -> epsilon and p' -L-> p
    #
    # L is essentially a prefix (which may be empty), T is a suffix that must be
    # able to derive an empty string.  State p' must lead to state p with the string L.
    #
    # -----------------------------------------------------------------------------

    def compute_lookback_includes(self, C, trans, nullable):
        lookdict = {}          # Dictionary of lookback relations
        includedict = {}       # Dictionary of include relations

        # Make a dictionary of non-terminal transitions
        dtrans = {}
        for t in trans:
            dtrans[t] = 1

        # Loop over all transitions and compute lookbacks and includes
        for state, N in trans:
            lookb = []
            includes = []
            for p in C[state]:
                if p.name != N:
                    continue

                # Okay, we have a name match.  We now follow the production all the way
                # through the state machine until we get the . on the right hand side

                lr_index = p.lr_index
                j = state
                while lr_index < p.len - 1:
                    lr_index = lr_index + 1
                    t = p.prod[lr_index]

                    # Check to see if this symbol and state are a non-terminal transition
                    if (j, t) in dtrans:
                        # Yes.  Okay, there is some chance that this is an includes relation
                        # the only way to know for certain is whether the rest of the
                        # production derives empty

                        li = lr_index + 1
                        while li < p.len:
                            if p.prod[li] in self.grammar.Terminals:
                                break      # No forget it
                            if p.prod[li] not in nullable:
                                break
                            li = li + 1
                        else:
                            # Appears to be a relation between (j,t) and (state,N)
                            includes.append((j, t))

                    g = self.lr0_goto(C[j], t)               # Go to next set
                    j = self.lr0_cidhash.get(id(g), -1)      # Go to next state

                # When we get here, j is the final state, now we have to locate the production
                for r in C[j]:
                    if r.name != p.name:
                        continue
                    if r.len != p.len:
                        continue
                    i = 0
                    # This look is comparing a production ". A B C" with "A B C ."
                    while i < r.lr_index:
                        if r.prod[i] != p.prod[i+1]:
                            break
                        i = i + 1
                    else:
                        lookb.append((j, r))
            for i in includes:
                if i not in includedict:
                    includedict[i] = []
                includedict[i].append((state, N))
            lookdict[(state, N)] = lookb

        return lookdict, includedict

    # -----------------------------------------------------------------------------
    # compute_read_sets()
    #
    # Given a set of LR(0) items, this function computes the read sets.
    #
    # Inputs:  C        =  Set of LR(0) items
    #          ntrans   = Set of nonterminal transitions
    #          nullable = Set of empty transitions
    #
    # Returns a set containing the read sets
    # -----------------------------------------------------------------------------

    def compute_read_sets(self, C, ntrans, nullable):
        FP = lambda x: self.dr_relation(C, x, nullable)
        R =  lambda x: self.reads_relation(C, x, nullable)
        F = digraph(ntrans, R, FP)
        return F

    # -----------------------------------------------------------------------------
    # compute_follow_sets()
    #
    # Given a set of LR(0) items, a set of non-terminal transitions, a readset,
    # and an include set, this function computes the follow sets
    #
    # Follow(p,A) = Read(p,A) U U {Follow(p',B) | (p,A) INCLUDES (p',B)}
    #
    # Inputs:
    #            ntrans     = Set of nonterminal transitions
    #            readsets   = Readset (previously computed)
    #            inclsets   = Include sets (previously computed)
    #
    # Returns a set containing the follow sets
    # -----------------------------------------------------------------------------

    def compute_follow_sets(self, ntrans, readsets, inclsets):
        FP = lambda x: readsets[x]
        R  = lambda x: inclsets.get(x, [])
        F = digraph(ntrans, R, FP)
        return F

    # -----------------------------------------------------------------------------
    # add_lookaheads()
    #
    # Attaches the lookahead symbols to grammar rules.
    #
    # Inputs:    lookbacks         -  Set of lookback relations
    #            followset         -  Computed follow set
    #
    # This function directly attaches the lookaheads to productions contained
    # in the lookbacks set
    # -----------------------------------------------------------------------------

    def add_lookaheads(self, lookbacks, followset):
        for trans, lb in lookbacks.items():
            # Loop over productions in lookback
            for state, p in lb:
                if state not in p.lookaheads:
                    p.lookaheads[state] = []
                f = followset.get(trans, [])
                for a in f:
                    if a not in p.lookaheads[state]:
                        p.lookaheads[state].append(a)

    # -----------------------------------------------------------------------------
    # add_lalr_lookaheads()
    #
    # This function does all of the work of adding lookahead information for use
    # with LALR parsing
    # -----------------------------------------------------------------------------

    def add_lalr_lookaheads(self, C):
        # Determine all of the nullable nonterminals
        nullable = self.compute_nullable_nonterminals()

        # Find all non-terminal transitions
        trans = self.find_nonterminal_transitions(C)

        # Compute read sets
        readsets = self.compute_read_sets(C, trans, nullable)

        # Compute lookback/includes relations
        lookd, included = self.compute_lookback_includes(C, trans, nullable)

        # Compute LALR FOLLOW sets
        followsets = self.compute_follow_sets(trans, readsets, included)

        # Add all of the lookaheads
        self.add_lookaheads(lookd, followsets)

    # -----------------------------------------------------------------------------
    # lr_parse_table()
    #
    # This function constructs the parse tables for SLR or LALR
    # -----------------------------------------------------------------------------
    def lr_parse_table(self):
        Productions = self.grammar.Productions
        Precedence  = self.grammar.Precedence
        goto   = self.lr_goto         # Goto array
        action = self.lr_action       # Action array
        log    = self.log             # Logger for output

        actionp = {}                  # Action production array (temporary)

        log.info('Parsing method: %s', self.lr_method)

        # Step 1: Construct C = { I0, I1, ... IN}, collection of LR(0) items
        # This determines the number of states

        C = self.lr0_items()

        if self.lr_method == 'LALR':
            self.add_lalr_lookaheads(C)

        # Build the parser table, state by state
        st = 0
        for I in C:
            # Loop over each production in I
            actlist = []              # List of actions
            st_action  = {}
            st_actionp = {}
            st_goto    = {}
            log.info('')
            log.info('state %d', st)
            log.info('')
            for p in I:
                log.info('    (%d) %s', p.number, p)
            log.info('')

            for p in I:
                    if p.len == p.lr_index + 1:
                        if p.name == "S'":
                            # Start symbol. Accept!
                            st_action['$end'] = 0
                            st_actionp['$end'] = p
                        else:
                            # We are at the end of a production.  Reduce!
                            if self.lr_method == 'LALR':
                                laheads = p.lookaheads[st]
                            else:
                                laheads = self.grammar.Follow[p.name]
                            for a in laheads:
                                actlist.append((a, p, 'reduce using rule %d (%s)' % (p.number, p)))
                                r = st_action.get(a)
                                if r is not None:
                                    # Whoa. Have a shift/reduce or reduce/reduce conflict
                                    if r > 0:
                                        # Need to decide on shift or reduce here
                                        # By default we favor shifting. Need to add
                                        # some precedence rules here.

                                        # Shift precedence comes from the token
                                        sprec, slevel = Precedence.get(a, ('right', 0))

                                        # Reduce precedence comes from rule being reduced (p)
                                        rprec, rlevel = Productions[p.number].prec

                                        if (slevel < rlevel) or ((slevel == rlevel) and (rprec == 'left')):
                                            # We really need to reduce here.
                                            st_action[a] = -p.number
                                            st_actionp[a] = p
                                            if not slevel and not rlevel:
                                                log.info('  ! shift/reduce conflict for %s resolved as reduce', a)
                                                self.sr_conflicts.append((st, a, 'reduce'))
                                            Productions[p.number].reduced += 1
                                        elif (slevel == rlevel) and (rprec == 'nonassoc'):
                                            st_action[a] = None
                                        else:
                                            # Hmmm. Guess we'll keep the shift
                                            if not rlevel:
                                                log.info('  ! shift/reduce conflict for %s resolved as shift', a)
                                                self.sr_conflicts.append((st, a, 'shift'))
                                    elif r < 0:
                                        # Reduce/reduce conflict.   In this case, we favor the rule
                                        # that was defined first in the grammar file
                                        oldp = Productions[-r]
                                        pp = Productions[p.number]
                                        if oldp.line > pp.line:
                                            st_action[a] = -p.number
                                            st_actionp[a] = p
                                            chosenp, rejectp = pp, oldp
                                            Productions[p.number].reduced += 1
                                            Productions[oldp.number].reduced -= 1
                                        else:
                                            chosenp, rejectp = oldp, pp
                                        self.rr_conflicts.append((st, chosenp, rejectp))
                                        log.info('  ! reduce/reduce conflict for %s resolved using rule %d (%s)',
                                                 a, st_actionp[a].number, st_actionp[a])
                                    else:
                                        raise LALRError('Unknown conflict in state %d' % st)
                                else:
                                    st_action[a] = -p.number
                                    st_actionp[a] = p
                                    Productions[p.number].reduced += 1
                    else:
                        i = p.lr_index
                        a = p.prod[i+1]       # Get symbol right after the "."
                        if a in self.grammar.Terminals:
                            g = self.lr0_goto(I, a)
                            j = self.lr0_cidhash.get(id(g), -1)
                            if j >= 0:
                                # We are in a shift state
                                actlist.append((a, p, 'shift and go to state %d' % j))
                                r = st_action.get(a)
                                if r is not None:
                                    # Whoa have a shift/reduce or shift/shift conflict
                                    if r > 0:
                                        if r != j:
                                            raise LALRError('Shift/shift conflict in state %d' % st)
                                    elif r < 0:
                                        # Do a precedence check.
                                        #   -  if precedence of reduce rule is higher, we reduce.
                                        #   -  if precedence of reduce is same and left assoc, we reduce.
                                        #   -  otherwise we shift

                                        # Shift precedence comes from the token
                                        sprec, slevel = Precedence.get(a, ('right', 0))

                                        # Reduce precedence comes from the rule that could have been reduced
                                        rprec, rlevel = Productions[st_actionp[a].number].prec

                                        if (slevel > rlevel) or ((slevel == rlevel) and (rprec == 'right')):
                                            # We decide to shift here... highest precedence to shift
                                            Productions[st_actionp[a].number].reduced -= 1
                                            st_action[a] = j
                                            st_actionp[a] = p
                                            if not rlevel:
                                                log.info('  ! shift/reduce conflict for %s resolved as shift', a)
                                                self.sr_conflicts.append((st, a, 'shift'))
                                        elif (slevel == rlevel) and (rprec == 'nonassoc'):
                                            st_action[a] = None
                                        else:
                                            # Hmmm. Guess we'll keep the reduce
                                            if not slevel and not rlevel:
                                                log.info('  ! shift/reduce conflict for %s resolved as reduce', a)
                                                self.sr_conflicts.append((st, a, 'reduce'))

                                    else:
                                        raise LALRError('Unknown conflict in state %d' % st)
                                else:
                                    st_action[a] = j
                                    st_actionp[a] = p

            # Print the actions associated with each terminal
            _actprint = {}
            for a, p, m in actlist:
                if a in st_action:
                    if p is st_actionp[a]:
                        log.info('    %-15s %s', a, m)
                        _actprint[(a, m)] = 1
            log.info('')
            # Print the actions that were not used. (debugging)
            not_used = 0
            for a, p, m in actlist:
                if a in st_action:
                    if p is not st_actionp[a]:
                        if not (a, m) in _actprint:
                            log.debug('  ! %-15s [ %s ]', a, m)
                            not_used = 1
                            _actprint[(a, m)] = 1
            if not_used:
                log.debug('')

            # Construct the goto table for this state

            nkeys = {}
            for ii in I:
                for s in ii.usyms:
                    if s in self.grammar.Nonterminals:
                        nkeys[s] = None
            for n in nkeys:
                g = self.lr0_goto(I, n)
                j = self.lr0_cidhash.get(id(g), -1)
                if j >= 0:
                    st_goto[n] = j
                    log.info('    %-30s shift and go to state %d', n, j)

            action[st] = st_action
            actionp[st] = st_actionp
            goto[st] = st_goto
            st += 1

    # -----------------------------------------------------------------------------
    # write()
    #
    # This function writes the LR parsing tables to a file
    # -----------------------------------------------------------------------------

    def write_table(self, tabmodule, outputdir='', signature=''):
        if isinstance(tabmodule, types.ModuleType):
            raise IOError("Won't overwrite existing tabmodule")

        basemodulename = tabmodule.split('.')[-1]
        filename = os.path.join(outputdir, basemodulename) + '.py'
        try:
            f = open(filename, 'w')

            f.write('''
# %s
# This file is automatically generated. Do not edit.
_tabversion = %r

_lr_method = %r

_lr_signature = %r
    ''' % (os.path.basename(filename), __tabversion__, self.lr_method, signature))

            # Change smaller to 0 to go back to original tables
            smaller = 1

            # Factor out names to try and make smaller
            if smaller:
                items = {}

                for s, nd in self.lr_action.items():
                    for name, v in nd.items():
                        i = items.get(name)
                        if not i:
                            i = ([], [])
                            items[name] = i
                        i[0].append(s)
                        i[1].append(v)

                f.write('\n_lr_action_items = {')
                for k, v in items.items():
                    f.write('%r:([' % k)
                    for i in v[0]:
                        f.write('%r,' % i)
                    f.write('],[')
                    for i in v[1]:
                        f.write('%r,' % i)

                    f.write(']),')
                f.write('}\n')

                f.write('''
_lr_action = {}
for _k, _v in _lr_action_items.items():
   for _x,_y in zip(_v[0],_v[1]):
      if not _x in _lr_action:  _lr_action[_x] = {}
      _lr_action[_x][_k] = _y
del _lr_action_items
''')

            else:
                f.write('\n_lr_action = { ')
                for k, v in self.lr_action.items():
                    f.write('(%r,%r):%r,' % (k[0], k[1], v))
                f.write('}\n')

            if smaller:
                # Factor out names to try and make smaller
                items = {}

                for s, nd in self.lr_goto.items():
                    for name, v in nd.items():
                        i = items.get(name)
                        if not i:
                            i = ([], [])
                            items[name] = i
                        i[0].append(s)
                        i[1].append(v)

                f.write('\n_lr_goto_items = {')
                for k, v in items.items():
                    f.write('%r:([' % k)
                    for i in v[0]:
                        f.write('%r,' % i)
                    f.write('],[')
                    for i in v[1]:
                        f.write('%r,' % i)

                    f.write(']),')
                f.write('}\n')

                f.write('''
_lr_goto = {}
for _k, _v in _lr_goto_items.items():
   for _x, _y in zip(_v[0], _v[1]):
       if not _x in _lr_goto: _lr_goto[_x] = {}
       _lr_goto[_x][_k] = _y
del _lr_goto_items
''')
            else:
                f.write('\n_lr_goto = { ')
                for k, v in self.lr_goto.items():
                    f.write('(%r,%r):%r,' % (k[0], k[1], v))
                f.write('}\n')

            # Write production table
            f.write('_lr_productions = [\n')
            for p in self.lr_productions:
                if p.func:
                    f.write('  (%r,%r,%d,%r,%r,%d),\n' % (p.str, p.name, p.len,
                                                          p.func, os.path.basename(p.file), p.line))
                else:
                    f.write('  (%r,%r,%d,None,None,None),\n' % (str(p), p.name, p.len))
            f.write(']\n')
            f.close()

        except IOError as e:
            raise


    # -----------------------------------------------------------------------------
    # pickle_table()
    #
    # This function pickles the LR parsing tables to a supplied file object
    # -----------------------------------------------------------------------------

    def pickle_table(self, filename, signature=''):
        try:
            import cPickle as pickle
        except ImportError:
            import pickle
        with open(filename, 'wb') as outf:
            pickle.dump(__tabversion__, outf, pickle_protocol)
            pickle.dump(self.lr_method, outf, pickle_protocol)
            pickle.dump(signature, outf, pickle_protocol)
            pickle.dump(self.lr_action, outf, pickle_protocol)
            pickle.dump(self.lr_goto, outf, pickle_protocol)

            outp = []
            for p in self.lr_productions:
                if p.func:
                    outp.append((p.str, p.name, p.len, p.func, os.path.basename(p.file), p.line))
                else:
                    outp.append((str(p), p.name, p.len, None, None, None))
            pickle.dump(outp, outf, pickle_protocol)

# -----------------------------------------------------------------------------
#                            === INTROSPECTION ===
#
# The following functions and classes are used to implement the PLY
# introspection features followed by the yacc() function itself.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# get_caller_module_dict()
#
# This function returns a dictionary containing all of the symbols defined within
# a caller further down the call stack.  This is used to get the environment
# associated with the yacc() call if none was provided.
# -----------------------------------------------------------------------------

def get_caller_module_dict(levels):
    f = sys._getframe(levels)
    ldict = f.f_globals.copy()
    if f.f_globals != f.f_locals:
        ldict.update(f.f_locals)
    return ldict

# -----------------------------------------------------------------------------
# parse_grammar()
#
# This takes a raw grammar rule string and parses it into production data
# -----------------------------------------------------------------------------
def parse_grammar(doc, file, line):
    grammar = []
    # Split the doc string into lines
    pstrings = doc.splitlines()
    lastp = None
    dline = line
    for ps in pstrings:
        dline += 1
        p = ps.split()
        if not p:
            continue
        try:
            if p[0] == '|':
                # This is a continuation of a previous rule
                if not lastp:
                    raise SyntaxError("%s:%d: Misplaced '|'" % (file, dline))
                prodname = lastp
                syms = p[1:]
            else:
                prodname = p[0]
                lastp = prodname
                syms   = p[2:]
                assign = p[1]
                if assign != ':' and assign != '::=':
                    raise SyntaxError("%s:%d: Syntax error. Expected ':'" % (file, dline))

            grammar.append((file, dline, prodname, syms))
        except SyntaxError:
            raise
        except Exception:
            raise SyntaxError('%s:%d: Syntax error in rule %r' % (file, dline, ps.strip()))

    return grammar

# -----------------------------------------------------------------------------
# ParserReflect()
#
# This class represents information extracted for building a parser including
# start symbol, error function, tokens, precedence list, action functions,
# etc.
# -----------------------------------------------------------------------------
class ParserReflect(object):
    def __init__(self, pdict, log=None):
        self.pdict      = pdict
        self.start      = None
        self.error_func = None
        self.tokens     = None
        self.modules    = set()
        self.grammar    = []
        self.error      = False

        if log is None:
            self.log = PlyLogger(sys.stderr)
        else:
            self.log = log

    # Get all of the basic information
    def get_all(self):
        self.get_start()
        self.get_error_func()
        self.get_tokens()
        self.get_precedence()
        self.get_pfunctions()

    # Validate all of the information
    def validate_all(self):
        self.validate_start()
        self.validate_error_func()
        self.validate_tokens()
        self.validate_precedence()
        self.validate_pfunctions()
        self.validate_modules()
        return self.error

    # Compute a signature over the grammar
    def signature(self):
        parts = []
        try:
            if self.start:
                parts.append(self.start)
            if self.prec:
                parts.append(''.join([''.join(p) for p in self.prec]))
            if self.tokens:
                parts.append(' '.join(self.tokens))
            for f in self.pfuncs:
                if f[3]:
                    parts.append(f[3])
        except (TypeError, ValueError):
            pass
        return ''.join(parts)

    # -----------------------------------------------------------------------------
    # validate_modules()
    #
    # This method checks to see if there are duplicated p_rulename() functions
    # in the parser module file.  Without this function, it is really easy for
    # users to make mistakes by cutting and pasting code fragments (and it's a real
    # bugger to try and figure out why the resulting parser doesn't work).  Therefore,
    # we just do a little regular expression pattern matching of def statements
    # to try and detect duplicates.
    # -----------------------------------------------------------------------------

    def validate_modules(self):
        # Match def p_funcname(
        fre = re.compile(r'\s*def\s+(p_[a-zA-Z_0-9]*)\(')

        for module in self.modules:
            try:
                lines, linen = inspect.getsourcelines(module)
            except IOError:
                continue

            counthash = {}
            for linen, line in enumerate(lines):
                linen += 1
                m = fre.match(line)
                if m:
                    name = m.group(1)
                    prev = counthash.get(name)
                    if not prev:
                        counthash[name] = linen
                    else:
                        filename = inspect.getsourcefile(module)
                        self.log.warning('%s:%d: Function %s redefined. Previously defined on line %d',
                                         filename, linen, name, prev)

    # Get the start symbol
    def get_start(self):
        self.start = self.pdict.get('start')

    # Validate the start symbol
    def validate_start(self):
        if self.start is not None:
            if not isinstance(self.start, string_types):
                self.log.error("'start' must be a string")

    # Look for error handler
    def get_error_func(self):
        self.error_func = self.pdict.get('p_error')

    # Validate the error function
    def validate_error_func(self):
        if self.error_func:
            if isinstance(self.error_func, types.FunctionType):
                ismethod = 0
            elif isinstance(self.error_func, types.MethodType):
                ismethod = 1
            else:
                self.log.error("'p_error' defined, but is not a function or method")
                self.error = True
                return

            eline = self.error_func.__code__.co_firstlineno
            efile = self.error_func.__code__.co_filename
            module = inspect.getmodule(self.error_func)
            self.modules.add(module)

            argcount = self.error_func.__code__.co_argcount - ismethod
            if argcount != 1:
                self.log.error('%s:%d: p_error() requires 1 argument', efile, eline)
                self.error = True

    # Get the tokens map
    def get_tokens(self):
        tokens = self.pdict.get('tokens')
        if not tokens:
            self.log.error('No token list is defined')
            self.error = True
            return

        if not isinstance(tokens, (list, tuple)):
            self.log.error('tokens must be a list or tuple')
            self.error = True
            return

        if not tokens:
            self.log.error('tokens is empty')
            self.error = True
            return

        self.tokens = tokens

    # Validate the tokens
    def validate_tokens(self):
        # Validate the tokens.
        if 'error' in self.tokens:
            self.log.error("Illegal token name 'error'. Is a reserved word")
            self.error = True
            return

        terminals = set()
        for n in self.tokens:
            if n in terminals:
                self.log.warning('Token %r multiply defined', n)
            terminals.add(n)

    # Get the precedence map (if any)
    def get_precedence(self):
        self.prec = self.pdict.get('precedence')

    # Validate and parse the precedence map
    def validate_precedence(self):
        preclist = []
        if self.prec:
            if not isinstance(self.prec, (list, tuple)):
                self.log.error('precedence must be a list or tuple')
                self.error = True
                return
            for level, p in enumerate(self.prec):
                if not isinstance(p, (list, tuple)):
                    self.log.error('Bad precedence table')
                    self.error = True
                    return

                if len(p) < 2:
                    self.log.error('Malformed precedence entry %s. Must be (assoc, term, ..., term)', p)
                    self.error = True
                    return
                assoc = p[0]
                if not isinstance(assoc, string_types):
                    self.log.error('precedence associativity must be a string')
                    self.error = True
                    return
                for term in p[1:]:
                    if not isinstance(term, string_types):
                        self.log.error('precedence items must be strings')
                        self.error = True
                        return
                    preclist.append((term, assoc, level+1))
        self.preclist = preclist

    # Get all p_functions from the grammar
    def get_pfunctions(self):
        p_functions = []
        for name, item in self.pdict.items():
            if not name.startswith('p_') or name == 'p_error':
                continue
            if isinstance(item, (types.FunctionType, types.MethodType)):
                line = getattr(item, 'co_firstlineno', item.__code__.co_firstlineno)
                module = inspect.getmodule(item)
                p_functions.append((line, module, name, item.__doc__))

        # Sort all of the actions by line number; make sure to stringify
        # modules to make them sortable, since `line` may not uniquely sort all
        # p functions
        p_functions.sort(key=lambda p_function: (
            p_function[0],
            str(p_function[1]),
            p_function[2],
            p_function[3]))
        self.pfuncs = p_functions

    # Validate all of the p_functions
    def validate_pfunctions(self):
        grammar = []
        # Check for non-empty symbols
        if len(self.pfuncs) == 0:
            self.log.error('no rules of the form p_rulename are defined')
            self.error = True
            return

        for line, module, name, doc in self.pfuncs:
            file = inspect.getsourcefile(module)
            func = self.pdict[name]
            if isinstance(func, types.MethodType):
                reqargs = 2
            else:
                reqargs = 1
            if func.__code__.co_argcount > reqargs:
                self.log.error('%s:%d: Rule %r has too many arguments', file, line, func.__name__)
                self.error = True
            elif func.__code__.co_argcount < reqargs:
                self.log.error('%s:%d: Rule %r requires an argument', file, line, func.__name__)
                self.error = True
            elif not func.__doc__:
                self.log.warning('%s:%d: No documentation string specified in function %r (ignored)',
                                 file, line, func.__name__)
            else:
                try:
                    parsed_g = parse_grammar(doc, file, line)
                    for g in parsed_g:
                        grammar.append((name, g))
                except SyntaxError as e:
                    self.log.error(str(e))
                    self.error = True

                # Looks like a valid grammar rule
                # Mark the file in which defined.
                self.modules.add(module)

        # Secondary validation step that looks for p_ definitions that are not functions
        # or functions that look like they might be grammar rules.

        for n, v in self.pdict.items():
            if n.startswith('p_') and isinstance(v, (types.FunctionType, types.MethodType)):
                continue
            if n.startswith('t_'):
                continue
            if n.startswith('p_') and n != 'p_error':
                self.log.warning('%r not defined as a function', n)
            if ((isinstance(v, types.FunctionType) and v.__code__.co_argcount == 1) or
                   (isinstance(v, types.MethodType) and v.__func__.__code__.co_argcount == 2)):
                if v.__doc__:
                    try:
                        doc = v.__doc__.split(' ')
                        if doc[1] == ':':
                            self.log.warning('%s:%d: Possible grammar rule %r defined without p_ prefix',
                                             v.__code__.co_filename, v.__code__.co_firstlineno, n)
                    except IndexError:
                        pass

        self.grammar = grammar

# -----------------------------------------------------------------------------
# yacc(module)
#
# Build a parser
# -----------------------------------------------------------------------------

def yacc(method='LALR', debug=yaccdebug, module=None, tabmodule=tab_module, start=None,
         check_recursion=True, optimize=False, write_tables=True, debugfile=debug_file,
         outputdir=None, debuglog=None, errorlog=None, picklefile=None):

    if tabmodule is None:
        tabmodule = tab_module

    # Reference to the parsing method of the last built parser
    global parse

    # If pickling is enabled, table files are not created
    if picklefile:
        write_tables = 0

    if errorlog is None:
        errorlog = PlyLogger(sys.stderr)

    # Get the module dictionary used for the parser
    if module:
        _items = [(k, getattr(module, k)) for k in dir(module)]
        pdict = dict(_items)
        # If no __file__ attribute is available, try to obtain it from the __module__ instead
        if '__file__' not in pdict:
            pdict['__file__'] = sys.modules[pdict['__module__']].__file__
    else:
        pdict = get_caller_module_dict(2)

    if outputdir is None:
        # If no output directory is set, the location of the output files
        # is determined according to the following rules:
        #     - If tabmodule specifies a package, files go into that package directory
        #     - Otherwise, files go in the same directory as the specifying module
        if isinstance(tabmodule, types.ModuleType):
            srcfile = tabmodule.__file__
        else:
            if '.' not in tabmodule:
                srcfile = pdict['__file__']
            else:
                parts = tabmodule.split('.')
                pkgname = '.'.join(parts[:-1])
                exec('import %s' % pkgname)
                srcfile = getattr(sys.modules[pkgname], '__file__', '')
        outputdir = os.path.dirname(srcfile)

    # Determine if the module is package of a package or not.
    # If so, fix the tabmodule setting so that tables load correctly
    pkg = pdict.get('__package__')
    if pkg and isinstance(tabmodule, str):
        if '.' not in tabmodule:
            tabmodule = pkg + '.' + tabmodule



    # Set start symbol if it's specified directly using an argument
    if start is not None:
        pdict['start'] = start

    # Collect parser information from the dictionary
    pinfo = ParserReflect(pdict, log=errorlog)
    pinfo.get_all()

    if pinfo.error:
        raise YaccError('Unable to build parser')

    # Check signature against table files (if any)
    signature = pinfo.signature()

    # Read the tables
    try:
        lr = LRTable()
        if picklefile:
            read_signature = lr.read_pickle(picklefile)
        else:
            read_signature = lr.read_table(tabmodule)
        if optimize or (read_signature == signature):
            try:
                lr.bind_callables(pinfo.pdict)
                parser = LRParser(lr, pinfo.error_func)
                parse = parser.parse
                return parser
            except Exception as e:
                errorlog.warning('There was a problem loading the table file: %r', e)
    except VersionError as e:
        errorlog.warning(str(e))
    except ImportError:
        pass

    if debuglog is None:
        if debug:
            try:
                debuglog = PlyLogger(open(os.path.join(outputdir, debugfile), 'w'))
            except IOError as e:
                errorlog.warning("Couldn't open %r. %s" % (debugfile, e))
                debuglog = NullLogger()
        else:
            debuglog = NullLogger()

    debuglog.info('Created by PLY version %s (http://www.dabeaz.com/ply)', __version__)

    errors = False

    # Validate the parser information
    if pinfo.validate_all():
        raise YaccError('Unable to build parser')

    if not pinfo.error_func:
        errorlog.warning('no p_error() function is defined')

    # Create a grammar object
    grammar = Grammar(pinfo.tokens)

    # Set precedence level for terminals
    for term, assoc, level in pinfo.preclist:
        try:
            grammar.set_precedence(term, assoc, level)
        except GrammarError as e:
            errorlog.warning('%s', e)

    # Add productions to the grammar
    for funcname, gram in pinfo.grammar:
        file, line, prodname, syms = gram
        try:
            grammar.add_production(prodname, syms, funcname, file, line)
        except GrammarError as e:
            errorlog.error('%s', e)
            errors = True

    # Set the grammar start symbols
    try:
        if start is None:
            grammar.set_start(pinfo.start)
        else:
            grammar.set_start(start)
    except GrammarError as e:
        errorlog.error(str(e))
        errors = True

    if errors:
        raise YaccError('Unable to build parser')

    # Verify the grammar structure
    undefined_symbols = grammar.undefined_symbols()
    for sym, prod in undefined_symbols:
        errorlog.error('%s:%d: Symbol %r used, but not defined as a token or a rule', prod.file, prod.line, sym)
        errors = True

    unused_terminals = grammar.unused_terminals()
    if unused_terminals:
        debuglog.info('')
        debuglog.info('Unused terminals:')
        debuglog.info('')
        for term in unused_terminals:
            errorlog.warning('Token %r defined, but not used', term)
            debuglog.info('    %s', term)

    # Print out all productions to the debug log
    if debug:
        debuglog.info('')
        debuglog.info('Grammar')
        debuglog.info('')
        for n, p in enumerate(grammar.Productions):
            debuglog.info('Rule %-5d %s', n, p)

    # Find unused non-terminals
    unused_rules = grammar.unused_rules()
    for prod in unused_rules:
        errorlog.warning('%s:%d: Rule %r defined, but not used', prod.file, prod.line, prod.name)

    if len(unused_terminals) == 1:
        errorlog.warning('There is 1 unused token')
    if len(unused_terminals) > 1:
        errorlog.warning('There are %d unused tokens', len(unused_terminals))

    if len(unused_rules) == 1:
        errorlog.warning('There is 1 unused rule')
    if len(unused_rules) > 1:
        errorlog.warning('There are %d unused rules', len(unused_rules))

    if debug:
        debuglog.info('')
        debuglog.info('Terminals, with rules where they appear')
        debuglog.info('')
        terms = list(grammar.Terminals)
        terms.sort()
        for term in terms:
            debuglog.info('%-20s : %s', term, ' '.join([str(s) for s in grammar.Terminals[term]]))

        debuglog.info('')
        debuglog.info('Nonterminals, with rules where they appear')
        debuglog.info('')
        nonterms = list(grammar.Nonterminals)
        nonterms.sort()
        for nonterm in nonterms:
            debuglog.info('%-20s : %s', nonterm, ' '.join([str(s) for s in grammar.Nonterminals[nonterm]]))
        debuglog.info('')

    if check_recursion:
        unreachable = grammar.find_unreachable()
        for u in unreachable:
            errorlog.warning('Symbol %r is unreachable', u)

        infinite = grammar.infinite_cycles()
        for inf in infinite:
            errorlog.error('Infinite recursion detected for symbol %r', inf)
            errors = True

    unused_prec = grammar.unused_precedence()
    for term, assoc in unused_prec:
        errorlog.error('Precedence rule %r defined for unknown symbol %r', assoc, term)
        errors = True

    if errors:
        raise YaccError('Unable to build parser')

    # Run the LRGeneratedTable on the grammar
    if debug:
        errorlog.debug('Generating %s tables', method)

    lr = LRGeneratedTable(grammar, method, debuglog)

    if debug:
        num_sr = len(lr.sr_conflicts)

        # Report shift/reduce and reduce/reduce conflicts
        if num_sr == 1:
            errorlog.warning('1 shift/reduce conflict')
        elif num_sr > 1:
            errorlog.warning('%d shift/reduce conflicts', num_sr)

        num_rr = len(lr.rr_conflicts)
        if num_rr == 1:
            errorlog.warning('1 reduce/reduce conflict')
        elif num_rr > 1:
            errorlog.warning('%d reduce/reduce conflicts', num_rr)

    # Write out conflicts to the output file
    if debug and (lr.sr_conflicts or lr.rr_conflicts):
        debuglog.warning('')
        debuglog.warning('Conflicts:')
        debuglog.warning('')

        for state, tok, resolution in lr.sr_conflicts:
            debuglog.warning('shift/reduce conflict for %s in state %d resolved as %s',  tok, state, resolution)

        already_reported = set()
        for state, rule, rejected in lr.rr_conflicts:
            if (state, id(rule), id(rejected)) in already_reported:
                continue
            debuglog.warning('reduce/reduce conflict in state %d resolved using rule (%s)', state, rule)
            debuglog.warning('rejected rule (%s) in state %d', rejected, state)
            errorlog.warning('reduce/reduce conflict in state %d resolved using rule (%s)', state, rule)
            errorlog.warning('rejected rule (%s) in state %d', rejected, state)
            already_reported.add((state, id(rule), id(rejected)))

        warned_never = []
        for state, rule, rejected in lr.rr_conflicts:
            if not rejected.reduced and (rejected not in warned_never):
                debuglog.warning('Rule (%s) is never reduced', rejected)
                errorlog.warning('Rule (%s) is never reduced', rejected)
                warned_never.append(rejected)

    # Write the table file if requested
    if write_tables:
        try:
            lr.write_table(tabmodule, outputdir, signature)
        except IOError as e:
            errorlog.warning("Couldn't create %r. %s" % (tabmodule, e))

    # Write a pickled version of the tables
    if picklefile:
        try:
            lr.pickle_table(picklefile, signature)
        except IOError as e:
            errorlog.warning("Couldn't create %r. %s" % (picklefile, e))

    # Build the parser
    lr.bind_callables(pinfo.pdict)
    parser = LRParser(lr, pinfo.error_func)

    parse = parser.parse
    return parser

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_client.py ===
# coding=utf-8
# Copyright 2023-present, the HuggingFace Inc. team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Related resources:
#    https://huggingface.co/tasks
#    https://huggingface.co/docs/huggingface.js/inference/README
#    https://github.com/huggingface/huggingface.js/tree/main/packages/inference/src
#    https://github.com/huggingface/text-generation-inference/tree/main/clients/python
#    https://github.com/huggingface/text-generation-inference/blob/main/clients/python/text_generation/client.py
#    https://huggingface.slack.com/archives/C03E4DQ9LAJ/p1680169099087869
#    https://github.com/huggingface/unity-api#tasks
#
# Some TODO:
# - add all tasks
#
# NOTE: the philosophy of this client is "let's make it as easy as possible to use it, even if less optimized". Some
# examples of how it translates:
# - Timeout / Server unavailable is handled by the client in a single "timeout" parameter.
# - Files can be provided as bytes, file paths, or URLs and the client will try to "guess" the type.
# - Images are parsed as PIL.Image for easier manipulation.
# - Provides a "recommended model" for each task => suboptimal but user-wise quicker to get a first script running.
# - Only the main parameters are publicly exposed. Power users can always read the docs for more options.
import base64
import logging
import re
import warnings
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Literal, Optional, Union, overload

from requests import HTTPError

from huggingface_hub import constants
from huggingface_hub.errors import BadRequestError, InferenceTimeoutError
from huggingface_hub.inference._common import (
    TASKS_EXPECTING_IMAGES,
    ContentT,
    ModelStatus,
    RequestParameters,
    _b64_encode,
    _b64_to_image,
    _bytes_to_dict,
    _bytes_to_image,
    _bytes_to_list,
    _get_unsupported_text_generation_kwargs,
    _import_numpy,
    _open_as_binary,
    _set_unsupported_text_generation_kwargs,
    _stream_chat_completion_response,
    _stream_text_generation_response,
    raise_text_generation_error,
)
from huggingface_hub.inference._generated.types import (
    AudioClassificationOutputElement,
    AudioClassificationOutputTransform,
    AudioToAudioOutputElement,
    AutomaticSpeechRecognitionOutput,
    ChatCompletionInputGrammarType,
    ChatCompletionInputMessage,
    ChatCompletionInputStreamOptions,
    ChatCompletionInputTool,
    ChatCompletionInputToolChoiceClass,
    ChatCompletionInputToolChoiceEnum,
    ChatCompletionOutput,
    ChatCompletionStreamOutput,
    DocumentQuestionAnsweringOutputElement,
    FillMaskOutputElement,
    ImageClassificationOutputElement,
    ImageClassificationOutputTransform,
    ImageSegmentationOutputElement,
    ImageSegmentationSubtask,
    ImageToImageTargetSize,
    ImageToTextOutput,
    ObjectDetectionOutputElement,
    Padding,
    QuestionAnsweringOutputElement,
    SummarizationOutput,
    SummarizationTruncationStrategy,
    TableQuestionAnsweringOutputElement,
    TextClassificationOutputElement,
    TextClassificationOutputTransform,
    TextGenerationInputGrammarType,
    TextGenerationOutput,
    TextGenerationStreamOutput,
    TextToSpeechEarlyStoppingEnum,
    TokenClassificationAggregationStrategy,
    TokenClassificationOutputElement,
    TranslationOutput,
    TranslationTruncationStrategy,
    VisualQuestionAnsweringOutputElement,
    ZeroShotClassificationOutputElement,
    ZeroShotImageClassificationOutputElement,
)
from huggingface_hub.inference._providers import PROVIDER_OR_POLICY_T, get_provider_helper
from huggingface_hub.utils import build_hf_headers, get_session, hf_raise_for_status
from huggingface_hub.utils._auth import get_token
from huggingface_hub.utils._deprecation import _deprecate_method


if TYPE_CHECKING:
    import numpy as np
    from PIL.Image import Image

logger = logging.getLogger(__name__)


MODEL_KWARGS_NOT_USED_REGEX = re.compile(r"The following `model_kwargs` are not used by the model: \[(.*?)\]")


class InferenceClient:
    """
    Initialize a new Inference Client.

    [`InferenceClient`] aims to provide a unified experience to perform inference. The client can be used
    seamlessly with either the (free) Inference API, self-hosted Inference Endpoints, or third-party Inference Providers.

    Args:
        model (`str`, `optional`):
            The model to run inference with. Can be a model id hosted on the Hugging Face Hub, e.g. `meta-llama/Meta-Llama-3-8B-Instruct`
            or a URL to a deployed Inference Endpoint. Defaults to None, in which case a recommended model is
            automatically selected for the task.
            Note: for better compatibility with OpenAI's client, `model` has been aliased as `base_url`. Those 2
            arguments are mutually exclusive. If using `base_url` for chat completion, the `/chat/completions` suffix
            path will be appended to the base URL (see the [TGI Messages API](https://huggingface.co/docs/text-generation-inference/en/messages_api)
            documentation for details). When passing a URL as `model`, the client will not append any suffix path to it.
        provider (`str`, *optional*):
            Name of the provider to use for inference. Can be `"black-forest-labs"`, `"cerebras"`, `"cohere"`, `"fal-ai"`, `"featherless-ai"`, `"fireworks-ai"`, `"groq"`, `"hf-inference"`, `"hyperbolic"`, `"nebius"`, `"novita"`, `"nscale"`, `"openai"`, `"replicate"`, "sambanova"` or `"together"`.
            Defaults to "auto" i.e. the first of the providers available for the model, sorted by the user's order in https://hf.co/settings/inference-providers.
            If model is a URL or `base_url` is passed, then `provider` is not used.
        token (`str`, *optional*):
            Hugging Face token. Will default to the locally saved token if not provided.
            Note: for better compatibility with OpenAI's client, `token` has been aliased as `api_key`. Those 2
            arguments are mutually exclusive and have the exact same behavior.
        timeout (`float`, `optional`):
            The maximum number of seconds to wait for a response from the server. Defaults to None, meaning it will loop until the server is available.
        headers (`Dict[str, str]`, `optional`):
            Additional headers to send to the server. By default only the authorization and user-agent headers are sent.
            Values in this dictionary will override the default values.
        bill_to (`str`, `optional`):
            The billing account to use for the requests. By default the requests are billed on the user's account.
            Requests can only be billed to an organization the user is a member of, and which has subscribed to Enterprise Hub.
        cookies (`Dict[str, str]`, `optional`):
            Additional cookies to send to the server.
        proxies (`Any`, `optional`):
            Proxies to use for the request.
        base_url (`str`, `optional`):
            Base URL to run inference. This is a duplicated argument from `model` to make [`InferenceClient`]
            follow the same pattern as `openai.OpenAI` client. Cannot be used if `model` is set. Defaults to None.
        api_key (`str`, `optional`):
            Token to use for authentication. This is a duplicated argument from `token` to make [`InferenceClient`]
            follow the same pattern as `openai.OpenAI` client. Cannot be used if `token` is set. Defaults to None.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        *,
        provider: Optional[PROVIDER_OR_POLICY_T] = None,
        token: Optional[str] = None,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        proxies: Optional[Any] = None,
        bill_to: Optional[str] = None,
        # OpenAI compatibility
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        if model is not None and base_url is not None:
            raise ValueError(
                "Received both `model` and `base_url` arguments. Please provide only one of them."
                " `base_url` is an alias for `model` to make the API compatible with OpenAI's client."
                " If using `base_url` for chat completion, the `/chat/completions` suffix path will be appended to the base url."
                " When passing a URL as `model`, the client will not append any suffix path to it."
            )
        if token is not None and api_key is not None:
            raise ValueError(
                "Received both `token` and `api_key` arguments. Please provide only one of them."
                " `api_key` is an alias for `token` to make the API compatible with OpenAI's client."
                " It has the exact same behavior as `token`."
            )
        token = token if token is not None else api_key
        if isinstance(token, bool):
            # Legacy behavior: previously is was possible to pass `token=False` to disable authentication. This is not
            # supported anymore as authentication is required. Better to explicitly raise here rather than risking
            # sending the locally saved token without the user knowing about it.
            if token is False:
                raise ValueError(
                    "Cannot use `token=False` to disable authentication as authentication is required to run Inference."
                )
            warnings.warn(
                "Using `token=True` to automatically use the locally saved token is deprecated and will be removed in a future release. "
                "Please use `token=None` instead (default).",
                DeprecationWarning,
            )
            token = get_token()

        self.model: Optional[str] = base_url or model
        self.token: Optional[str] = token

        self.headers = {**headers} if headers is not None else {}
        if bill_to is not None:
            if (
                constants.HUGGINGFACE_HEADER_X_BILL_TO in self.headers
                and self.headers[constants.HUGGINGFACE_HEADER_X_BILL_TO] != bill_to
            ):
                warnings.warn(
                    f"Overriding existing '{self.headers[constants.HUGGINGFACE_HEADER_X_BILL_TO]}' value in headers with '{bill_to}'.",
                    UserWarning,
                )
            self.headers[constants.HUGGINGFACE_HEADER_X_BILL_TO] = bill_to

            if token is not None and not token.startswith("hf_"):
                warnings.warn(
                    "You've provided an external provider's API key, so requests will be billed directly by the provider. "
                    "The `bill_to` parameter is only applicable for Hugging Face billing and will be ignored.",
                    UserWarning,
                )

        # Configure provider
        self.provider = provider

        self.cookies = cookies
        self.timeout = timeout
        self.proxies = proxies

    def __repr__(self):
        return f"<InferenceClient(model='{self.model if self.model else ''}', timeout={self.timeout})>"

    @overload
    def _inner_post(  # type: ignore[misc]
        self, request_parameters: RequestParameters, *, stream: Literal[False] = ...
    ) -> bytes: ...

    @overload
    def _inner_post(  # type: ignore[misc]
        self, request_parameters: RequestParameters, *, stream: Literal[True] = ...
    ) -> Iterable[bytes]: ...

    @overload
    def _inner_post(
        self, request_parameters: RequestParameters, *, stream: bool = False
    ) -> Union[bytes, Iterable[bytes]]: ...

    def _inner_post(
        self, request_parameters: RequestParameters, *, stream: bool = False
    ) -> Union[bytes, Iterable[bytes]]:
        """Make a request to the inference server."""
        # TODO: this should be handled in provider helpers directly
        if request_parameters.task in TASKS_EXPECTING_IMAGES and "Accept" not in request_parameters.headers:
            request_parameters.headers["Accept"] = "image/png"

        with _open_as_binary(request_parameters.data) as data_as_binary:
            try:
                response = get_session().post(
                    request_parameters.url,
                    json=request_parameters.json,
                    data=data_as_binary,
                    headers=request_parameters.headers,
                    cookies=self.cookies,
                    timeout=self.timeout,
                    stream=stream,
                    proxies=self.proxies,
                )
            except TimeoutError as error:
                # Convert any `TimeoutError` to a `InferenceTimeoutError`
                raise InferenceTimeoutError(f"Inference call timed out: {request_parameters.url}") from error  # type: ignore

        try:
            hf_raise_for_status(response)
            return response.iter_lines() if stream else response.content
        except HTTPError as error:
            if error.response.status_code == 422 and request_parameters.task != "unknown":
                msg = str(error.args[0])
                if len(error.response.text) > 0:
                    msg += f"\n{error.response.text}\n"
                error.args = (msg,) + error.args[1:]
            raise

    def audio_classification(
        self,
        audio: ContentT,
        *,
        model: Optional[str] = None,
        top_k: Optional[int] = None,
        function_to_apply: Optional["AudioClassificationOutputTransform"] = None,
    ) -> List[AudioClassificationOutputElement]:
        """
        Perform audio classification on the provided audio content.

        Args:
            audio (Union[str, Path, bytes, BinaryIO]):
                The audio content to classify. It can be raw audio bytes, a local audio file, or a URL pointing to an
                audio file.
            model (`str`, *optional*):
                The model to use for audio classification. Can be a model ID hosted on the Hugging Face Hub
                or a URL to a deployed Inference Endpoint. If not provided, the default recommended model for
                audio classification will be used.
            top_k (`int`, *optional*):
                When specified, limits the output to the top K most probable classes.
            function_to_apply (`"AudioClassificationOutputTransform"`, *optional*):
                The function to apply to the model outputs in order to retrieve the scores.

        Returns:
            `List[AudioClassificationOutputElement]`: List of [`AudioClassificationOutputElement`] items containing the predicted labels and their confidence.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.audio_classification("audio.flac")
        [
            AudioClassificationOutputElement(score=0.4976358711719513, label='hap'),
            AudioClassificationOutputElement(score=0.3677836060523987, label='neu'),
            ...
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="audio-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=audio,
            parameters={"function_to_apply": function_to_apply, "top_k": top_k},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return AudioClassificationOutputElement.parse_obj_as_list(response)

    def audio_to_audio(
        self,
        audio: ContentT,
        *,
        model: Optional[str] = None,
    ) -> List[AudioToAudioOutputElement]:
        """
        Performs multiple tasks related to audio-to-audio depending on the model (eg: speech enhancement, source separation).

        Args:
            audio (Union[str, Path, bytes, BinaryIO]):
                The audio content for the model. It can be raw audio bytes, a local audio file, or a URL pointing to an
                audio file.
            model (`str`, *optional*):
                The model can be any model which takes an audio file and returns another audio file. Can be a model ID hosted on the Hugging Face Hub
                or a URL to a deployed Inference Endpoint. If not provided, the default recommended model for
                audio_to_audio will be used.

        Returns:
            `List[AudioToAudioOutputElement]`: A list of [`AudioToAudioOutputElement`] items containing audios label, content-type, and audio content in blob.

        Raises:
            `InferenceTimeoutError`:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> audio_output = client.audio_to_audio("audio.flac")
        >>> for i, item in enumerate(audio_output):
        >>>     with open(f"output_{i}.flac", "wb") as f:
                    f.write(item.blob)
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="audio-to-audio", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=audio,
            parameters={},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        audio_output = AudioToAudioOutputElement.parse_obj_as_list(response)
        for item in audio_output:
            item.blob = base64.b64decode(item.blob)
        return audio_output

    def automatic_speech_recognition(
        self,
        audio: ContentT,
        *,
        model: Optional[str] = None,
        extra_body: Optional[Dict] = None,
    ) -> AutomaticSpeechRecognitionOutput:
        """
        Perform automatic speech recognition (ASR or audio-to-text) on the given audio content.

        Args:
            audio (Union[str, Path, bytes, BinaryIO]):
                The content to transcribe. It can be raw audio bytes, local audio file, or a URL to an audio file.
            model (`str`, *optional*):
                The model to use for ASR. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended model for ASR will be used.
            extra_body (`Dict`, *optional*):
                Additional provider-specific parameters to pass to the model. Refer to the provider's documentation
                for supported parameters.
        Returns:
            [`AutomaticSpeechRecognitionOutput`]: An item containing the transcribed text and optionally the timestamp chunks.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.automatic_speech_recognition("hello_world.flac").text
        "hello world"
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="automatic-speech-recognition", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=audio,
            parameters={**(extra_body or {})},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return AutomaticSpeechRecognitionOutput.parse_obj_as_instance(response)

    @overload
    def chat_completion(  # type: ignore
        self,
        messages: List[Union[Dict, ChatCompletionInputMessage]],
        *,
        model: Optional[str] = None,
        stream: Literal[False] = False,
        frequency_penalty: Optional[float] = None,
        logit_bias: Optional[List[float]] = None,
        logprobs: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        response_format: Optional[ChatCompletionInputGrammarType] = None,
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stream_options: Optional[ChatCompletionInputStreamOptions] = None,
        temperature: Optional[float] = None,
        tool_choice: Optional[Union[ChatCompletionInputToolChoiceClass, "ChatCompletionInputToolChoiceEnum"]] = None,
        tool_prompt: Optional[str] = None,
        tools: Optional[List[ChatCompletionInputTool]] = None,
        top_logprobs: Optional[int] = None,
        top_p: Optional[float] = None,
        extra_body: Optional[Dict] = None,
    ) -> ChatCompletionOutput: ...

    @overload
    def chat_completion(  # type: ignore
        self,
        messages: List[Union[Dict, ChatCompletionInputMessage]],
        *,
        model: Optional[str] = None,
        stream: Literal[True] = True,
        frequency_penalty: Optional[float] = None,
        logit_bias: Optional[List[float]] = None,
        logprobs: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        response_format: Optional[ChatCompletionInputGrammarType] = None,
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stream_options: Optional[ChatCompletionInputStreamOptions] = None,
        temperature: Optional[float] = None,
        tool_choice: Optional[Union[ChatCompletionInputToolChoiceClass, "ChatCompletionInputToolChoiceEnum"]] = None,
        tool_prompt: Optional[str] = None,
        tools: Optional[List[ChatCompletionInputTool]] = None,
        top_logprobs: Optional[int] = None,
        top_p: Optional[float] = None,
        extra_body: Optional[Dict] = None,
    ) -> Iterable[ChatCompletionStreamOutput]: ...

    @overload
    def chat_completion(
        self,
        messages: List[Union[Dict, ChatCompletionInputMessage]],
        *,
        model: Optional[str] = None,
        stream: bool = False,
        frequency_penalty: Optional[float] = None,
        logit_bias: Optional[List[float]] = None,
        logprobs: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        response_format: Optional[ChatCompletionInputGrammarType] = None,
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stream_options: Optional[ChatCompletionInputStreamOptions] = None,
        temperature: Optional[float] = None,
        tool_choice: Optional[Union[ChatCompletionInputToolChoiceClass, "ChatCompletionInputToolChoiceEnum"]] = None,
        tool_prompt: Optional[str] = None,
        tools: Optional[List[ChatCompletionInputTool]] = None,
        top_logprobs: Optional[int] = None,
        top_p: Optional[float] = None,
        extra_body: Optional[Dict] = None,
    ) -> Union[ChatCompletionOutput, Iterable[ChatCompletionStreamOutput]]: ...

    def chat_completion(
        self,
        messages: List[Union[Dict, ChatCompletionInputMessage]],
        *,
        model: Optional[str] = None,
        stream: bool = False,
        # Parameters from ChatCompletionInput (handled manually)
        frequency_penalty: Optional[float] = None,
        logit_bias: Optional[List[float]] = None,
        logprobs: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        response_format: Optional[ChatCompletionInputGrammarType] = None,
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stream_options: Optional[ChatCompletionInputStreamOptions] = None,
        temperature: Optional[float] = None,
        tool_choice: Optional[Union[ChatCompletionInputToolChoiceClass, "ChatCompletionInputToolChoiceEnum"]] = None,
        tool_prompt: Optional[str] = None,
        tools: Optional[List[ChatCompletionInputTool]] = None,
        top_logprobs: Optional[int] = None,
        top_p: Optional[float] = None,
        extra_body: Optional[Dict] = None,
    ) -> Union[ChatCompletionOutput, Iterable[ChatCompletionStreamOutput]]:
        """
        A method for completing conversations using a specified language model.

        <Tip>

        The `client.chat_completion` method is aliased as `client.chat.completions.create` for compatibility with OpenAI's client.
        Inputs and outputs are strictly the same and using either syntax will yield the same results.
        Check out the [Inference guide](https://huggingface.co/docs/huggingface_hub/guides/inference#openai-compatibility)
        for more details about OpenAI's compatibility.

        </Tip>

        <Tip>
        You can pass provider-specific parameters to the model by using the `extra_body` argument.
        </Tip>

        Args:
            messages (List of [`ChatCompletionInputMessage`]):
                Conversation history consisting of roles and content pairs.
            model (`str`, *optional*):
                The model to use for chat-completion. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended model for chat-based text-generation will be used.
                See https://huggingface.co/tasks/text-generation for more details.
                If `model` is a model ID, it is passed to the server as the `model` parameter. If you want to define a
                custom URL while setting `model` in the request payload, you must set `base_url` when initializing [`InferenceClient`].
            frequency_penalty (`float`, *optional*):
                Penalizes new tokens based on their existing frequency
                in the text so far. Range: [-2.0, 2.0]. Defaults to 0.0.
            logit_bias (`List[float]`, *optional*):
                Adjusts the likelihood of specific tokens appearing in the generated output.
            logprobs (`bool`, *optional*):
                Whether to return log probabilities of the output tokens or not. If true, returns the log
                probabilities of each output token returned in the content of message.
            max_tokens (`int`, *optional*):
                Maximum number of tokens allowed in the response. Defaults to 100.
            n (`int`, *optional*):
                The number of completions to generate for each prompt.
            presence_penalty (`float`, *optional*):
                Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the
                text so far, increasing the model's likelihood to talk about new topics.
            response_format ([`ChatCompletionInputGrammarType`], *optional*):
                Grammar constraints. Can be either a JSONSchema or a regex.
            seed (Optional[`int`], *optional*):
                Seed for reproducible control flow. Defaults to None.
            stop (`List[str]`, *optional*):
                Up to four strings which trigger the end of the response.
                Defaults to None.
            stream (`bool`, *optional*):
                Enable realtime streaming of responses. Defaults to False.
            stream_options ([`ChatCompletionInputStreamOptions`], *optional*):
                Options for streaming completions.
            temperature (`float`, *optional*):
                Controls randomness of the generations. Lower values ensure
                less random completions. Range: [0, 2]. Defaults to 1.0.
            top_logprobs (`int`, *optional*):
                An integer between 0 and 5 specifying the number of most likely tokens to return at each token
                position, each with an associated log probability. logprobs must be set to true if this parameter is
                used.
            top_p (`float`, *optional*):
                Fraction of the most likely next words to sample from.
                Must be between 0 and 1. Defaults to 1.0.
            tool_choice ([`ChatCompletionInputToolChoiceClass`] or [`ChatCompletionInputToolChoiceEnum`], *optional*):
                The tool to use for the completion. Defaults to "auto".
            tool_prompt (`str`, *optional*):
                A prompt to be appended before the tools.
            tools (List of [`ChatCompletionInputTool`], *optional*):
                A list of tools the model may call. Currently, only functions are supported as a tool. Use this to
                provide a list of functions the model may generate JSON inputs for.
            extra_body (`Dict`, *optional*):
                Additional provider-specific parameters to pass to the model. Refer to the provider's documentation
                for supported parameters.
        Returns:
            [`ChatCompletionOutput`] or Iterable of [`ChatCompletionStreamOutput`]:
            Generated text returned from the server:
            - if `stream=False`, the generated text is returned as a [`ChatCompletionOutput`] (default).
            - if `stream=True`, the generated text is returned token by token as a sequence of [`ChatCompletionStreamOutput`].

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:

        ```py
        >>> from huggingface_hub import InferenceClient
        >>> messages = [{"role": "user", "content": "What is the capital of France?"}]
        >>> client = InferenceClient("meta-llama/Meta-Llama-3-8B-Instruct")
        >>> client.chat_completion(messages, max_tokens=100)
        ChatCompletionOutput(
            choices=[
                ChatCompletionOutputComplete(
                    finish_reason='eos_token',
                    index=0,
                    message=ChatCompletionOutputMessage(
                        role='assistant',
                        content='The capital of France is Paris.',
                        name=None,
                        tool_calls=None
                    ),
                    logprobs=None
                )
            ],
            created=1719907176,
            id='',
            model='meta-llama/Meta-Llama-3-8B-Instruct',
            object='text_completion',
            system_fingerprint='2.0.4-sha-f426a33',
            usage=ChatCompletionOutputUsage(
                completion_tokens=8,
                prompt_tokens=17,
                total_tokens=25
            )
        )
        ```

        Example using streaming:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> messages = [{"role": "user", "content": "What is the capital of France?"}]
        >>> client = InferenceClient("meta-llama/Meta-Llama-3-8B-Instruct")
        >>> for token in client.chat_completion(messages, max_tokens=10, stream=True):
        ...     print(token)
        ChatCompletionStreamOutput(choices=[ChatCompletionStreamOutputChoice(delta=ChatCompletionStreamOutputDelta(content='The', role='assistant'), index=0, finish_reason=None)], created=1710498504)
        ChatCompletionStreamOutput(choices=[ChatCompletionStreamOutputChoice(delta=ChatCompletionStreamOutputDelta(content=' capital', role='assistant'), index=0, finish_reason=None)], created=1710498504)
        (...)
        ChatCompletionStreamOutput(choices=[ChatCompletionStreamOutputChoice(delta=ChatCompletionStreamOutputDelta(content=' may', role='assistant'), index=0, finish_reason=None)], created=1710498504)
        ```

        Example using OpenAI's syntax:
        ```py
        # instead of `from openai import OpenAI`
        from huggingface_hub import InferenceClient

        # instead of `client = OpenAI(...)`
        client = InferenceClient(
            base_url=...,
            api_key=...,
        )

        output = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Count to 10"},
            ],
            stream=True,
            max_tokens=1024,
        )

        for chunk in output:
            print(chunk.choices[0].delta.content)
        ```

        Example using a third-party provider directly with extra (provider-specific) parameters. Usage will be billed on your Together AI account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="together",  # Use Together AI provider
        ...     api_key="<together_api_key>",  # Pass your Together API key directly
        ... )
        >>> client.chat_completion(
        ...     model="meta-llama/Meta-Llama-3-8B-Instruct",
        ...     messages=[{"role": "user", "content": "What is the capital of France?"}],
        ...     extra_body={"safety_model": "Meta-Llama/Llama-Guard-7b"},
        ... )
        ```

        Example using a third-party provider through Hugging Face Routing. Usage will be billed on your Hugging Face account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="sambanova",  # Use Sambanova provider
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> client.chat_completion(
        ...     model="meta-llama/Meta-Llama-3-8B-Instruct",
        ...     messages=[{"role": "user", "content": "What is the capital of France?"}],
        ... )
        ```

        Example using Image + Text as input:
        ```py
        >>> from huggingface_hub import InferenceClient

        # provide a remote URL
        >>> image_url ="https://cdn.britannica.com/61/93061-050-99147DCE/Statue-of-Liberty-Island-New-York-Bay.jpg"
        # or a base64-encoded image
        >>> image_path = "/path/to/image.jpeg"
        >>> with open(image_path, "rb") as f:
        ...     base64_image = base64.b64encode(f.read()).decode("utf-8")
        >>> image_url = f"data:image/jpeg;base64,{base64_image}"

        >>> client = InferenceClient("meta-llama/Llama-3.2-11B-Vision-Instruct")
        >>> output = client.chat.completions.create(
        ...     messages=[
        ...         {
        ...             "role": "user",
        ...             "content": [
        ...                 {
        ...                     "type": "image_url",
        ...                     "image_url": {"url": image_url},
        ...                 },
        ...                 {
        ...                     "type": "text",
        ...                     "text": "Describe this image in one sentence.",
        ...                 },
        ...             ],
        ...         },
        ...     ],
        ... )
        >>> output
        The image depicts the iconic Statue of Liberty situated in New York Harbor, New York, on a clear day.
        ```

        Example using tools:
        ```py
        >>> client = InferenceClient("meta-llama/Meta-Llama-3-70B-Instruct")
        >>> messages = [
        ...     {
        ...         "role": "system",
        ...         "content": "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous.",
        ...     },
        ...     {
        ...         "role": "user",
        ...         "content": "What's the weather like the next 3 days in San Francisco, CA?",
        ...     },
        ... ]
        >>> tools = [
        ...     {
        ...         "type": "function",
        ...         "function": {
        ...             "name": "get_current_weather",
        ...             "description": "Get the current weather",
        ...             "parameters": {
        ...                 "type": "object",
        ...                 "properties": {
        ...                     "location": {
        ...                         "type": "string",
        ...                         "description": "The city and state, e.g. San Francisco, CA",
        ...                     },
        ...                     "format": {
        ...                         "type": "string",
        ...                         "enum": ["celsius", "fahrenheit"],
        ...                         "description": "The temperature unit to use. Infer this from the users location.",
        ...                     },
        ...                 },
        ...                 "required": ["location", "format"],
        ...             },
        ...         },
        ...     },
        ...     {
        ...         "type": "function",
        ...         "function": {
        ...             "name": "get_n_day_weather_forecast",
        ...             "description": "Get an N-day weather forecast",
        ...             "parameters": {
        ...                 "type": "object",
        ...                 "properties": {
        ...                     "location": {
        ...                         "type": "string",
        ...                         "description": "The city and state, e.g. San Francisco, CA",
        ...                     },
        ...                     "format": {
        ...                         "type": "string",
        ...                         "enum": ["celsius", "fahrenheit"],
        ...                         "description": "The temperature unit to use. Infer this from the users location.",
        ...                     },
        ...                     "num_days": {
        ...                         "type": "integer",
        ...                         "description": "The number of days to forecast",
        ...                     },
        ...                 },
        ...                 "required": ["location", "format", "num_days"],
        ...             },
        ...         },
        ...     },
        ... ]

        >>> response = client.chat_completion(
        ...     model="meta-llama/Meta-Llama-3-70B-Instruct",
        ...     messages=messages,
        ...     tools=tools,
        ...     tool_choice="auto",
        ...     max_tokens=500,
        ... )
        >>> response.choices[0].message.tool_calls[0].function
        ChatCompletionOutputFunctionDefinition(
            arguments={
                'location': 'San Francisco, CA',
                'format': 'fahrenheit',
                'num_days': 3
            },
            name='get_n_day_weather_forecast',
            description=None
        )
        ```

        Example using response_format:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient("meta-llama/Meta-Llama-3-70B-Instruct")
        >>> messages = [
        ...     {
        ...         "role": "user",
        ...         "content": "I saw a puppy a cat and a raccoon during my bike ride in the park. What did I saw and when?",
        ...     },
        ... ]
        >>> response_format = {
        ...     "type": "json",
        ...     "value": {
        ...         "properties": {
        ...             "location": {"type": "string"},
        ...             "activity": {"type": "string"},
        ...             "animals_seen": {"type": "integer", "minimum": 1, "maximum": 5},
        ...             "animals": {"type": "array", "items": {"type": "string"}},
        ...         },
        ...         "required": ["location", "activity", "animals_seen", "animals"],
        ...     },
        ... }
        >>> response = client.chat_completion(
        ...     messages=messages,
        ...     response_format=response_format,
        ...     max_tokens=500,
        ... )
        >>> response.choices[0].message.content
        '{\n\n"activity": "bike ride",\n"animals": ["puppy", "cat", "raccoon"],\n"animals_seen": 3,\n"location": "park"}'
        ```
        """
        # Since `chat_completion(..., model=xxx)` is also a payload parameter for the server, we need to handle 'model' differently.
        # `self.model` takes precedence over 'model' argument for building URL.
        # `model` takes precedence for payload value.
        model_id_or_url = self.model or model
        payload_model = model or self.model

        # Get the provider helper
        provider_helper = get_provider_helper(
            self.provider,
            task="conversational",
            model=model_id_or_url
            if model_id_or_url is not None and model_id_or_url.startswith(("http://", "https://"))
            else payload_model,
        )

        # Prepare the payload
        parameters = {
            "model": payload_model,
            "frequency_penalty": frequency_penalty,
            "logit_bias": logit_bias,
            "logprobs": logprobs,
            "max_tokens": max_tokens,
            "n": n,
            "presence_penalty": presence_penalty,
            "response_format": response_format,
            "seed": seed,
            "stop": stop,
            "temperature": temperature,
            "tool_choice": tool_choice,
            "tool_prompt": tool_prompt,
            "tools": tools,
            "top_logprobs": top_logprobs,
            "top_p": top_p,
            "stream": stream,
            "stream_options": stream_options,
            **(extra_body or {}),
        }
        request_parameters = provider_helper.prepare_request(
            inputs=messages,
            parameters=parameters,
            headers=self.headers,
            model=model_id_or_url,
            api_key=self.token,
        )
        data = self._inner_post(request_parameters, stream=stream)

        if stream:
            return _stream_chat_completion_response(data)  # type: ignore[arg-type]

        return ChatCompletionOutput.parse_obj_as_instance(data)  # type: ignore[arg-type]

    def document_question_answering(
        self,
        image: ContentT,
        question: str,
        *,
        model: Optional[str] = None,
        doc_stride: Optional[int] = None,
        handle_impossible_answer: Optional[bool] = None,
        lang: Optional[str] = None,
        max_answer_len: Optional[int] = None,
        max_question_len: Optional[int] = None,
        max_seq_len: Optional[int] = None,
        top_k: Optional[int] = None,
        word_boxes: Optional[List[Union[List[float], str]]] = None,
    ) -> List[DocumentQuestionAnsweringOutputElement]:
        """
        Answer questions on document images.

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The input image for the context. It can be raw bytes, an image file, or a URL to an online image.
            question (`str`):
                Question to be answered.
            model (`str`, *optional*):
                The model to use for the document question answering task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended document question answering model will be used.
                Defaults to None.
            doc_stride (`int`, *optional*):
                If the words in the document are too long to fit with the question for the model, it will be split in
                several chunks with some overlap. This argument controls the size of that overlap.
            handle_impossible_answer (`bool`, *optional*):
                Whether to accept impossible as an answer
            lang (`str`, *optional*):
                Language to use while running OCR. Defaults to english.
            max_answer_len (`int`, *optional*):
                The maximum length of predicted answers (e.g., only answers with a shorter length are considered).
            max_question_len (`int`, *optional*):
                The maximum length of the question after tokenization. It will be truncated if needed.
            max_seq_len (`int`, *optional*):
                The maximum length of the total sentence (context + question) in tokens of each chunk passed to the
                model. The context will be split in several chunks (using doc_stride as overlap) if needed.
            top_k (`int`, *optional*):
                The number of answers to return (will be chosen by order of likelihood). Can return less than top_k
                answers if there are not enough options available within the context.
            word_boxes (`List[Union[List[float], str`, *optional*):
                A list of words and bounding boxes (normalized 0->1000). If provided, the inference will skip the OCR
                step and use the provided bounding boxes instead.
        Returns:
            `List[DocumentQuestionAnsweringOutputElement]`: a list of [`DocumentQuestionAnsweringOutputElement`] items containing the predicted label, associated probability, word ids, and page number.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.


        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.document_question_answering(image="https://huggingface.co/spaces/impira/docquery/resolve/2359223c1837a7587402bda0f2643382a6eefeab/invoice.png", question="What is the invoice number?")
        [DocumentQuestionAnsweringOutputElement(answer='us-001', end=16, score=0.9999666213989258, start=16)]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="document-question-answering", model=model_id)
        inputs: Dict[str, Any] = {"question": question, "image": _b64_encode(image)}
        request_parameters = provider_helper.prepare_request(
            inputs=inputs,
            parameters={
                "doc_stride": doc_stride,
                "handle_impossible_answer": handle_impossible_answer,
                "lang": lang,
                "max_answer_len": max_answer_len,
                "max_question_len": max_question_len,
                "max_seq_len": max_seq_len,
                "top_k": top_k,
                "word_boxes": word_boxes,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return DocumentQuestionAnsweringOutputElement.parse_obj_as_list(response)

    def feature_extraction(
        self,
        text: str,
        *,
        normalize: Optional[bool] = None,
        prompt_name: Optional[str] = None,
        truncate: Optional[bool] = None,
        truncation_direction: Optional[Literal["Left", "Right"]] = None,
        model: Optional[str] = None,
    ) -> "np.ndarray":
        """
        Generate embeddings for a given text.

        Args:
            text (`str`):
                The text to embed.
            model (`str`, *optional*):
                The model to use for the feature extraction task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended feature extraction model will be used.
                Defaults to None.
            normalize (`bool`, *optional*):
                Whether to normalize the embeddings or not.
                Only available on server powered by Text-Embedding-Inference.
            prompt_name (`str`, *optional*):
                The name of the prompt that should be used by for encoding. If not set, no prompt will be applied.
                Must be a key in the `Sentence Transformers` configuration `prompts` dictionary.
                For example if ``prompt_name`` is "query" and the ``prompts`` is {"query": "query: ",...},
                then the sentence "What is the capital of France?" will be encoded as "query: What is the capital of France?"
                because the prompt text will be prepended before any text to encode.
            truncate (`bool`, *optional*):
                Whether to truncate the embeddings or not.
                Only available on server powered by Text-Embedding-Inference.
            truncation_direction (`Literal["Left", "Right"]`, *optional*):
                Which side of the input should be truncated when `truncate=True` is passed.

        Returns:
            `np.ndarray`: The embedding representing the input text as a float32 numpy array.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.feature_extraction("Hi, who are you?")
        array([[ 2.424802  ,  2.93384   ,  1.1750331 , ...,  1.240499, -0.13776633, -0.7889173 ],
        [-0.42943227, -0.6364878 , -1.693462  , ...,  0.41978157, -2.4336355 ,  0.6162071 ],
        ...,
        [ 0.28552425, -0.928395  , -1.2077185 , ...,  0.76810825, -2.1069427 ,  0.6236161 ]], dtype=float32)
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="feature-extraction", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "normalize": normalize,
                "prompt_name": prompt_name,
                "truncate": truncate,
                "truncation_direction": truncation_direction,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        np = _import_numpy()
        return np.array(provider_helper.get_response(response), dtype="float32")

    def fill_mask(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        targets: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> List[FillMaskOutputElement]:
        """
        Fill in a hole with a missing word (token to be precise).

        Args:
            text (`str`):
                a string to be filled from, must contain the [MASK] token (check model card for exact name of the mask).
            model (`str`, *optional*):
                The model to use for the fill mask task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended fill mask model will be used.
            targets (`List[str`, *optional*):
                When passed, the model will limit the scores to the passed targets instead of looking up in the whole
                vocabulary. If the provided targets are not in the model vocab, they will be tokenized and the first
                resulting token will be used (with a warning, and that might be slower).
            top_k (`int`, *optional*):
                When passed, overrides the number of predictions to return.
        Returns:
            `List[FillMaskOutputElement]`: a list of [`FillMaskOutputElement`] items containing the predicted label, associated
            probability, token reference, and completed text.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.fill_mask("The goal of life is <mask>.")
        [
            FillMaskOutputElement(score=0.06897063553333282, token=11098, token_str=' happiness', sequence='The goal of life is happiness.'),
            FillMaskOutputElement(score=0.06554922461509705, token=45075, token_str=' immortality', sequence='The goal of life is immortality.')
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="fill-mask", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={"targets": targets, "top_k": top_k},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return FillMaskOutputElement.parse_obj_as_list(response)

    def image_classification(
        self,
        image: ContentT,
        *,
        model: Optional[str] = None,
        function_to_apply: Optional["ImageClassificationOutputTransform"] = None,
        top_k: Optional[int] = None,
    ) -> List[ImageClassificationOutputElement]:
        """
        Perform image classification on the given image using the specified model.

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The image to classify. It can be raw bytes, an image file, or a URL to an online image.
            model (`str`, *optional*):
                The model to use for image classification. Can be a model ID hosted on the Hugging Face Hub or a URL to a
                deployed Inference Endpoint. If not provided, the default recommended model for image classification will be used.
            function_to_apply (`"ImageClassificationOutputTransform"`, *optional*):
                The function to apply to the model outputs in order to retrieve the scores.
            top_k (`int`, *optional*):
                When specified, limits the output to the top K most probable classes.
        Returns:
            `List[ImageClassificationOutputElement]`: a list of [`ImageClassificationOutputElement`] items containing the predicted label and associated probability.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.image_classification("https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Cute_dog.jpg/320px-Cute_dog.jpg")
        [ImageClassificationOutputElement(label='Blenheim spaniel', score=0.9779096841812134), ...]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="image-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={"function_to_apply": function_to_apply, "top_k": top_k},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return ImageClassificationOutputElement.parse_obj_as_list(response)

    def image_segmentation(
        self,
        image: ContentT,
        *,
        model: Optional[str] = None,
        mask_threshold: Optional[float] = None,
        overlap_mask_area_threshold: Optional[float] = None,
        subtask: Optional["ImageSegmentationSubtask"] = None,
        threshold: Optional[float] = None,
    ) -> List[ImageSegmentationOutputElement]:
        """
        Perform image segmentation on the given image using the specified model.

        <Tip warning={true}>

        You must have `PIL` installed if you want to work with images (`pip install Pillow`).

        </Tip>

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The image to segment. It can be raw bytes, an image file, or a URL to an online image.
            model (`str`, *optional*):
                The model to use for image segmentation. Can be a model ID hosted on the Hugging Face Hub or a URL to a
                deployed Inference Endpoint. If not provided, the default recommended model for image segmentation will be used.
            mask_threshold (`float`, *optional*):
                Threshold to use when turning the predicted masks into binary values.
            overlap_mask_area_threshold (`float`, *optional*):
                Mask overlap threshold to eliminate small, disconnected segments.
            subtask (`"ImageSegmentationSubtask"`, *optional*):
                Segmentation task to be performed, depending on model capabilities.
            threshold (`float`, *optional*):
                Probability threshold to filter out predicted masks.
        Returns:
            `List[ImageSegmentationOutputElement]`: A list of [`ImageSegmentationOutputElement`] items containing the segmented masks and associated attributes.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.image_segmentation("cat.jpg")
        [ImageSegmentationOutputElement(score=0.989008, label='LABEL_184', mask=<PIL.PngImagePlugin.PngImageFile image mode=L size=400x300 at 0x7FDD2B129CC0>), ...]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="image-segmentation", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={
                "mask_threshold": mask_threshold,
                "overlap_mask_area_threshold": overlap_mask_area_threshold,
                "subtask": subtask,
                "threshold": threshold,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        output = ImageSegmentationOutputElement.parse_obj_as_list(response)
        for item in output:
            item.mask = _b64_to_image(item.mask)  # type: ignore [assignment]
        return output

    def image_to_image(
        self,
        image: ContentT,
        prompt: Optional[str] = None,
        *,
        negative_prompt: Optional[str] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        model: Optional[str] = None,
        target_size: Optional[ImageToImageTargetSize] = None,
        **kwargs,
    ) -> "Image":
        """
        Perform image-to-image translation using a specified model.

        <Tip warning={true}>

        You must have `PIL` installed if you want to work with images (`pip install Pillow`).

        </Tip>

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The input image for translation. It can be raw bytes, an image file, or a URL to an online image.
            prompt (`str`, *optional*):
                The text prompt to guide the image generation.
            negative_prompt (`str`, *optional*):
                One prompt to guide what NOT to include in image generation.
            num_inference_steps (`int`, *optional*):
                For diffusion models. The number of denoising steps. More denoising steps usually lead to a higher
                quality image at the expense of slower inference.
            guidance_scale (`float`, *optional*):
                For diffusion models. A higher guidance scale value encourages the model to generate images closely
                linked to the text prompt at the expense of lower image quality.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. Defaults to None.
            target_size (`ImageToImageTargetSize`, *optional*):
                The size in pixel of the output image.

        Returns:
            `Image`: The translated image.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> image = client.image_to_image("cat.jpg", prompt="turn the cat into a tiger")
        >>> image.save("tiger.jpg")
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="image-to-image", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "target_size": target_size,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                **kwargs,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return _bytes_to_image(response)

    def image_to_text(self, image: ContentT, *, model: Optional[str] = None) -> ImageToTextOutput:
        """
        Takes an input image and return text.

        Models can have very different outputs depending on your use case (image captioning, optical character recognition
        (OCR), Pix2Struct, etc). Please have a look to the model card to learn more about a model's specificities.

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The input image to caption. It can be raw bytes, an image file, or a URL to an online image..
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. Defaults to None.

        Returns:
            [`ImageToTextOutput`]: The generated text.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.image_to_text("cat.jpg")
        'a cat standing in a grassy field '
        >>> client.image_to_text("https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Cute_dog.jpg/320px-Cute_dog.jpg")
        'a dog laying on the grass next to a flower pot '
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="image-to-text", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        output = ImageToTextOutput.parse_obj(response)
        return output[0] if isinstance(output, list) else output

    def object_detection(
        self, image: ContentT, *, model: Optional[str] = None, threshold: Optional[float] = None
    ) -> List[ObjectDetectionOutputElement]:
        """
        Perform object detection on the given image using the specified model.

        <Tip warning={true}>

        You must have `PIL` installed if you want to work with images (`pip install Pillow`).

        </Tip>

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The image to detect objects on. It can be raw bytes, an image file, or a URL to an online image.
            model (`str`, *optional*):
                The model to use for object detection. Can be a model ID hosted on the Hugging Face Hub or a URL to a
                deployed Inference Endpoint. If not provided, the default recommended model for object detection (DETR) will be used.
            threshold (`float`, *optional*):
                The probability necessary to make a prediction.
        Returns:
            `List[ObjectDetectionOutputElement]`: A list of [`ObjectDetectionOutputElement`] items containing the bounding boxes and associated attributes.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.
            `ValueError`:
                If the request output is not a List.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.object_detection("people.jpg")
        [ObjectDetectionOutputElement(score=0.9486683011054993, label='person', box=ObjectDetectionBoundingBox(xmin=59, ymin=39, xmax=420, ymax=510)), ...]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="object-detection", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={"threshold": threshold},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return ObjectDetectionOutputElement.parse_obj_as_list(response)

    def question_answering(
        self,
        question: str,
        context: str,
        *,
        model: Optional[str] = None,
        align_to_words: Optional[bool] = None,
        doc_stride: Optional[int] = None,
        handle_impossible_answer: Optional[bool] = None,
        max_answer_len: Optional[int] = None,
        max_question_len: Optional[int] = None,
        max_seq_len: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> Union[QuestionAnsweringOutputElement, List[QuestionAnsweringOutputElement]]:
        """
        Retrieve the answer to a question from a given text.

        Args:
            question (`str`):
                Question to be answered.
            context (`str`):
                The context of the question.
            model (`str`):
                The model to use for the question answering task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint.
            align_to_words (`bool`, *optional*):
                Attempts to align the answer to real words. Improves quality on space separated languages. Might hurt
                on non-space-separated languages (like Japanese or Chinese)
            doc_stride (`int`, *optional*):
                If the context is too long to fit with the question for the model, it will be split in several chunks
                with some overlap. This argument controls the size of that overlap.
            handle_impossible_answer (`bool`, *optional*):
                Whether to accept impossible as an answer.
            max_answer_len (`int`, *optional*):
                The maximum length of predicted answers (e.g., only answers with a shorter length are considered).
            max_question_len (`int`, *optional*):
                The maximum length of the question after tokenization. It will be truncated if needed.
            max_seq_len (`int`, *optional*):
                The maximum length of the total sentence (context + question) in tokens of each chunk passed to the
                model. The context will be split in several chunks (using docStride as overlap) if needed.
            top_k (`int`, *optional*):
                The number of answers to return (will be chosen by order of likelihood). Note that we return less than
                topk answers if there are not enough options available within the context.

        Returns:
            Union[`QuestionAnsweringOutputElement`, List[`QuestionAnsweringOutputElement`]]:
                When top_k is 1 or not provided, it returns a single `QuestionAnsweringOutputElement`.
                When top_k is greater than 1, it returns a list of `QuestionAnsweringOutputElement`.
        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.question_answering(question="What's my name?", context="My name is Clara and I live in Berkeley.")
        QuestionAnsweringOutputElement(answer='Clara', end=16, score=0.9326565265655518, start=11)
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="question-answering", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs={"question": question, "context": context},
            parameters={
                "align_to_words": align_to_words,
                "doc_stride": doc_stride,
                "handle_impossible_answer": handle_impossible_answer,
                "max_answer_len": max_answer_len,
                "max_question_len": max_question_len,
                "max_seq_len": max_seq_len,
                "top_k": top_k,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        # Parse the response as a single `QuestionAnsweringOutputElement` when top_k is 1 or not provided, or a list of `QuestionAnsweringOutputElement` to ensure backward compatibility.
        output = QuestionAnsweringOutputElement.parse_obj(response)
        return output

    def sentence_similarity(
        self, sentence: str, other_sentences: List[str], *, model: Optional[str] = None
    ) -> List[float]:
        """
        Compute the semantic similarity between a sentence and a list of other sentences by comparing their embeddings.

        Args:
            sentence (`str`):
                The main sentence to compare to others.
            other_sentences (`List[str]`):
                The list of sentences to compare to.
            model (`str`, *optional*):
                The model to use for the sentence similarity task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended sentence similarity model will be used.
                Defaults to None.

        Returns:
            `List[float]`: The embedding representing the input text.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.sentence_similarity(
        ...     "Machine learning is so easy.",
        ...     other_sentences=[
        ...         "Deep learning is so straightforward.",
        ...         "This is so difficult, like rocket science.",
        ...         "I can't believe how much I struggled with this.",
        ...     ],
        ... )
        [0.7785726189613342, 0.45876261591911316, 0.2906220555305481]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="sentence-similarity", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs={"source_sentence": sentence, "sentences": other_sentences},
            parameters={},
            extra_payload={},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return _bytes_to_list(response)

    def summarization(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        clean_up_tokenization_spaces: Optional[bool] = None,
        generate_parameters: Optional[Dict[str, Any]] = None,
        truncation: Optional["SummarizationTruncationStrategy"] = None,
    ) -> SummarizationOutput:
        """
        Generate a summary of a given text using a specified model.

        Args:
            text (`str`):
                The input text to summarize.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended model for summarization will be used.
            clean_up_tokenization_spaces (`bool`, *optional*):
                Whether to clean up the potential extra spaces in the text output.
            generate_parameters (`Dict[str, Any]`, *optional*):
                Additional parametrization of the text generation algorithm.
            truncation (`"SummarizationTruncationStrategy"`, *optional*):
                The truncation strategy to use.
        Returns:
            [`SummarizationOutput`]: The generated summary text.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.summarization("The Eiffel tower...")
        SummarizationOutput(generated_text="The Eiffel tower is one of the most famous landmarks in the world....")
        ```
        """
        parameters = {
            "clean_up_tokenization_spaces": clean_up_tokenization_spaces,
            "generate_parameters": generate_parameters,
            "truncation": truncation,
        }
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="summarization", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters=parameters,
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return SummarizationOutput.parse_obj_as_list(response)[0]

    def table_question_answering(
        self,
        table: Dict[str, Any],
        query: str,
        *,
        model: Optional[str] = None,
        padding: Optional["Padding"] = None,
        sequential: Optional[bool] = None,
        truncation: Optional[bool] = None,
    ) -> TableQuestionAnsweringOutputElement:
        """
        Retrieve the answer to a question from information given in a table.

        Args:
            table (`str`):
                A table of data represented as a dict of lists where entries are headers and the lists are all the
                values, all lists must have the same size.
            query (`str`):
                The query in plain text that you want to ask the table.
            model (`str`):
                The model to use for the table-question-answering task. Can be a model ID hosted on the Hugging Face
                Hub or a URL to a deployed Inference Endpoint.
            padding (`"Padding"`, *optional*):
                Activates and controls padding.
            sequential (`bool`, *optional*):
                Whether to do inference sequentially or as a batch. Batching is faster, but models like SQA require the
                inference to be done sequentially to extract relations within sequences, given their conversational
                nature.
            truncation (`bool`, *optional*):
                Activates and controls truncation.

        Returns:
            [`TableQuestionAnsweringOutputElement`]: a table question answering output containing the answer, coordinates, cells and the aggregator used.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> query = "How many stars does the transformers repository have?"
        >>> table = {"Repository": ["Transformers", "Datasets", "Tokenizers"], "Stars": ["36542", "4512", "3934"]}
        >>> client.table_question_answering(table, query, model="google/tapas-base-finetuned-wtq")
        TableQuestionAnsweringOutputElement(answer='36542', coordinates=[[0, 1]], cells=['36542'], aggregator='AVERAGE')
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="table-question-answering", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs={"query": query, "table": table},
            parameters={"model": model, "padding": padding, "sequential": sequential, "truncation": truncation},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return TableQuestionAnsweringOutputElement.parse_obj_as_instance(response)

    def tabular_classification(self, table: Dict[str, Any], *, model: Optional[str] = None) -> List[str]:
        """
        Classifying a target category (a group) based on a set of attributes.

        Args:
            table (`Dict[str, Any]`):
                Set of attributes to classify.
            model (`str`, *optional*):
                The model to use for the tabular classification task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended tabular classification model will be used.
                Defaults to None.

        Returns:
            `List`: a list of labels, one per row in the initial table.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> table = {
        ...     "fixed_acidity": ["7.4", "7.8", "10.3"],
        ...     "volatile_acidity": ["0.7", "0.88", "0.32"],
        ...     "citric_acid": ["0", "0", "0.45"],
        ...     "residual_sugar": ["1.9", "2.6", "6.4"],
        ...     "chlorides": ["0.076", "0.098", "0.073"],
        ...     "free_sulfur_dioxide": ["11", "25", "5"],
        ...     "total_sulfur_dioxide": ["34", "67", "13"],
        ...     "density": ["0.9978", "0.9968", "0.9976"],
        ...     "pH": ["3.51", "3.2", "3.23"],
        ...     "sulphates": ["0.56", "0.68", "0.82"],
        ...     "alcohol": ["9.4", "9.8", "12.6"],
        ... }
        >>> client.tabular_classification(table=table, model="julien-c/wine-quality")
        ["5", "5", "5"]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="tabular-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=None,
            extra_payload={"table": table},
            parameters={},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return _bytes_to_list(response)

    def tabular_regression(self, table: Dict[str, Any], *, model: Optional[str] = None) -> List[float]:
        """
        Predicting a numerical target value given a set of attributes/features in a table.

        Args:
            table (`Dict[str, Any]`):
                Set of attributes stored in a table. The attributes used to predict the target can be both numerical and categorical.
            model (`str`, *optional*):
                The model to use for the tabular regression task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended tabular regression model will be used.
                Defaults to None.

        Returns:
            `List`: a list of predicted numerical target values.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> table = {
        ...     "Height": ["11.52", "12.48", "12.3778"],
        ...     "Length1": ["23.2", "24", "23.9"],
        ...     "Length2": ["25.4", "26.3", "26.5"],
        ...     "Length3": ["30", "31.2", "31.1"],
        ...     "Species": ["Bream", "Bream", "Bream"],
        ...     "Width": ["4.02", "4.3056", "4.6961"],
        ... }
        >>> client.tabular_regression(table, model="scikit-learn/Fish-Weight")
        [110, 120, 130]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="tabular-regression", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=None,
            parameters={},
            extra_payload={"table": table},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return _bytes_to_list(response)

    def text_classification(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        top_k: Optional[int] = None,
        function_to_apply: Optional["TextClassificationOutputTransform"] = None,
    ) -> List[TextClassificationOutputElement]:
        """
        Perform text classification (e.g. sentiment-analysis) on the given text.

        Args:
            text (`str`):
                A string to be classified.
            model (`str`, *optional*):
                The model to use for the text classification task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended text classification model will be used.
                Defaults to None.
            top_k (`int`, *optional*):
                When specified, limits the output to the top K most probable classes.
            function_to_apply (`"TextClassificationOutputTransform"`, *optional*):
                The function to apply to the model outputs in order to retrieve the scores.

        Returns:
            `List[TextClassificationOutputElement]`: a list of [`TextClassificationOutputElement`] items containing the predicted label and associated probability.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.text_classification("I like you")
        [
            TextClassificationOutputElement(label='POSITIVE', score=0.9998695850372314),
            TextClassificationOutputElement(label='NEGATIVE', score=0.0001304351753788069),
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="text-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "function_to_apply": function_to_apply,
                "top_k": top_k,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return TextClassificationOutputElement.parse_obj_as_list(response)[0]  # type: ignore [return-value]

    @overload
    def text_generation(  # type: ignore
        self,
        prompt: str,
        *,
        details: Literal[False] = ...,
        stream: Literal[False] = ...,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> str: ...

    @overload
    def text_generation(  # type: ignore
        self,
        prompt: str,
        *,
        details: Literal[True] = ...,
        stream: Literal[False] = ...,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> TextGenerationOutput: ...

    @overload
    def text_generation(  # type: ignore
        self,
        prompt: str,
        *,
        details: Literal[False] = ...,
        stream: Literal[True] = ...,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> Iterable[str]: ...

    @overload
    def text_generation(  # type: ignore
        self,
        prompt: str,
        *,
        details: Literal[True] = ...,
        stream: Literal[True] = ...,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> Iterable[TextGenerationStreamOutput]: ...

    @overload
    def text_generation(
        self,
        prompt: str,
        *,
        details: Literal[True] = ...,
        stream: bool = ...,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> Union[TextGenerationOutput, Iterable[TextGenerationStreamOutput]]: ...

    def text_generation(
        self,
        prompt: str,
        *,
        details: bool = False,
        stream: bool = False,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> Union[str, TextGenerationOutput, Iterable[str], Iterable[TextGenerationStreamOutput]]:
        """
        Given a prompt, generate the following text.

        <Tip>

        If you want to generate a response from chat messages, you should use the [`InferenceClient.chat_completion`] method.
        It accepts a list of messages instead of a single text prompt and handles the chat templating for you.

        </Tip>

        Args:
            prompt (`str`):
                Input text.
            details (`bool`, *optional*):
                By default, text_generation returns a string. Pass `details=True` if you want a detailed output (tokens,
                probabilities, seed, finish reason, etc.). Only available for models running on with the
                `text-generation-inference` backend.
            stream (`bool`, *optional*):
                By default, text_generation returns the full generated text. Pass `stream=True` if you want a stream of
                tokens to be returned. Only available for models running on with the `text-generation-inference`
                backend.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. Defaults to None.
            adapter_id (`str`, *optional*):
                Lora adapter id.
            best_of (`int`, *optional*):
                Generate best_of sequences and return the one if the highest token logprobs.
            decoder_input_details (`bool`, *optional*):
                Return the decoder input token logprobs and ids. You must set `details=True` as well for it to be taken
                into account. Defaults to `False`.
            do_sample (`bool`, *optional*):
                Activate logits sampling
            frequency_penalty (`float`, *optional*):
                Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in
                the text so far, decreasing the model's likelihood to repeat the same line verbatim.
            grammar ([`TextGenerationInputGrammarType`], *optional*):
                Grammar constraints. Can be either a JSONSchema or a regex.
            max_new_tokens (`int`, *optional*):
                Maximum number of generated tokens. Defaults to 100.
            repetition_penalty (`float`, *optional*):
                The parameter for repetition penalty. 1.0 means no penalty. See [this
                paper](https://arxiv.org/pdf/1909.05858.pdf) for more details.
            return_full_text (`bool`, *optional*):
                Whether to prepend the prompt to the generated text
            seed (`int`, *optional*):
                Random sampling seed
            stop (`List[str]`, *optional*):
                Stop generating tokens if a member of `stop` is generated.
            stop_sequences (`List[str]`, *optional*):
                Deprecated argument. Use `stop` instead.
            temperature (`float`, *optional*):
                The value used to module the logits distribution.
            top_n_tokens (`int`, *optional*):
                Return information about the `top_n_tokens` most likely tokens at each generation step, instead of
                just the sampled token.
            top_k (`int`, *optional`):
                The number of highest probability vocabulary tokens to keep for top-k-filtering.
            top_p (`float`, *optional`):
                If set to < 1, only the smallest set of most probable tokens with probabilities that add up to `top_p` or
                higher are kept for generation.
            truncate (`int`, *optional`):
                Truncate inputs tokens to the given size.
            typical_p (`float`, *optional`):
                Typical Decoding mass
                See [Typical Decoding for Natural Language Generation](https://arxiv.org/abs/2202.00666) for more information
            watermark (`bool`, *optional`):
                Watermarking with [A Watermark for Large Language Models](https://arxiv.org/abs/2301.10226)

        Returns:
            `Union[str, TextGenerationOutput, Iterable[str], Iterable[TextGenerationStreamOutput]]`:
            Generated text returned from the server:
            - if `stream=False` and `details=False`, the generated text is returned as a `str` (default)
            - if `stream=True` and `details=False`, the generated text is returned token by token as a `Iterable[str]`
            - if `stream=False` and `details=True`, the generated text is returned with more details as a [`~huggingface_hub.TextGenerationOutput`]
            - if `details=True` and `stream=True`, the generated text is returned token by token as a iterable of [`~huggingface_hub.TextGenerationStreamOutput`]

        Raises:
            `ValidationError`:
                If input values are not valid. No HTTP call is made to the server.
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()

        # Case 1: generate text
        >>> client.text_generation("The huggingface_hub library is ", max_new_tokens=12)
        '100% open source and built to be easy to use.'

        # Case 2: iterate over the generated tokens. Useful for large generation.
        >>> for token in client.text_generation("The huggingface_hub library is ", max_new_tokens=12, stream=True):
        ...     print(token)
        100
        %
        open
        source
        and
        built
        to
        be
        easy
        to
        use
        .

        # Case 3: get more details about the generation process.
        >>> client.text_generation("The huggingface_hub library is ", max_new_tokens=12, details=True)
        TextGenerationOutput(
            generated_text='100% open source and built to be easy to use.',
            details=TextGenerationDetails(
                finish_reason='length',
                generated_tokens=12,
                seed=None,
                prefill=[
                    TextGenerationPrefillOutputToken(id=487, text='The', logprob=None),
                    TextGenerationPrefillOutputToken(id=53789, text=' hugging', logprob=-13.171875),
                    (...)
                    TextGenerationPrefillOutputToken(id=204, text=' ', logprob=-7.0390625)
                ],
                tokens=[
                    TokenElement(id=1425, text='100', logprob=-1.0175781, special=False),
                    TokenElement(id=16, text='%', logprob=-0.0463562, special=False),
                    (...)
                    TokenElement(id=25, text='.', logprob=-0.5703125, special=False)
                ],
                best_of_sequences=None
            )
        )

        # Case 4: iterate over the generated tokens with more details.
        # Last object is more complete, containing the full generated text and the finish reason.
        >>> for details in client.text_generation("The huggingface_hub library is ", max_new_tokens=12, details=True, stream=True):
        ...     print(details)
        ...
        TextGenerationStreamOutput(token=TokenElement(id=1425, text='100', logprob=-1.0175781, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=16, text='%', logprob=-0.0463562, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=1314, text=' open', logprob=-1.3359375, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=3178, text=' source', logprob=-0.28100586, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=273, text=' and', logprob=-0.5961914, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=3426, text=' built', logprob=-1.9423828, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=271, text=' to', logprob=-1.4121094, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=314, text=' be', logprob=-1.5224609, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=1833, text=' easy', logprob=-2.1132812, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=271, text=' to', logprob=-0.08520508, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=745, text=' use', logprob=-0.39453125, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(
            id=25,
            text='.',
            logprob=-0.5703125,
            special=False),
            generated_text='100% open source and built to be easy to use.',
            details=TextGenerationStreamOutputStreamDetails(finish_reason='length', generated_tokens=12, seed=None)
        )

        # Case 5: generate constrained output using grammar
        >>> response = client.text_generation(
        ...     prompt="I saw a puppy a cat and a raccoon during my bike ride in the park",
        ...     model="HuggingFaceH4/zephyr-orpo-141b-A35b-v0.1",
        ...     max_new_tokens=100,
        ...     repetition_penalty=1.3,
        ...     grammar={
        ...         "type": "json",
        ...         "value": {
        ...             "properties": {
        ...                 "location": {"type": "string"},
        ...                 "activity": {"type": "string"},
        ...                 "animals_seen": {"type": "integer", "minimum": 1, "maximum": 5},
        ...                 "animals": {"type": "array", "items": {"type": "string"}},
        ...             },
        ...             "required": ["location", "activity", "animals_seen", "animals"],
        ...         },
        ...     },
        ... )
        >>> json.loads(response)
        {
            "activity": "bike riding",
            "animals": ["puppy", "cat", "raccoon"],
            "animals_seen": 3,
            "location": "park"
        }
        ```
        """
        if decoder_input_details and not details:
            warnings.warn(
                "`decoder_input_details=True` has been passed to the server but `details=False` is set meaning that"
                " the output from the server will be truncated."
            )
            decoder_input_details = False

        if stop_sequences is not None:
            warnings.warn(
                "`stop_sequences` is a deprecated argument for `text_generation` task"
                " and will be removed in version '0.28.0'. Use `stop` instead.",
                FutureWarning,
            )
        if stop is None:
            stop = stop_sequences  # use deprecated arg if provided

        # Build payload
        parameters = {
            "adapter_id": adapter_id,
            "best_of": best_of,
            "decoder_input_details": decoder_input_details,
            "details": details,
            "do_sample": do_sample,
            "frequency_penalty": frequency_penalty,
            "grammar": grammar,
            "max_new_tokens": max_new_tokens,
            "repetition_penalty": repetition_penalty,
            "return_full_text": return_full_text,
            "seed": seed,
            "stop": stop if stop is not None else [],
            "temperature": temperature,
            "top_k": top_k,
            "top_n_tokens": top_n_tokens,
            "top_p": top_p,
            "truncate": truncate,
            "typical_p": typical_p,
            "watermark": watermark,
        }

        # Remove some parameters if not a TGI server
        unsupported_kwargs = _get_unsupported_text_generation_kwargs(model)
        if len(unsupported_kwargs) > 0:
            # The server does not support some parameters
            # => means it is not a TGI server
            # => remove unsupported parameters and warn the user

            ignored_parameters = []
            for key in unsupported_kwargs:
                if parameters.get(key):
                    ignored_parameters.append(key)
                parameters.pop(key, None)
            if len(ignored_parameters) > 0:
                warnings.warn(
                    "API endpoint/model for text-generation is not served via TGI. Ignoring following parameters:"
                    f" {', '.join(ignored_parameters)}.",
                    UserWarning,
                )
            if details:
                warnings.warn(
                    "API endpoint/model for text-generation is not served via TGI. Parameter `details=True` will"
                    " be ignored meaning only the generated text will be returned.",
                    UserWarning,
                )
                details = False
            if stream:
                raise ValueError(
                    "API endpoint/model for text-generation is not served via TGI. Cannot return output as a stream."
                    " Please pass `stream=False` as input."
                )

        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="text-generation", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=prompt,
            parameters=parameters,
            extra_payload={"stream": stream},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )

        # Handle errors separately for more precise error messages
        try:
            bytes_output = self._inner_post(request_parameters, stream=stream)
        except HTTPError as e:
            match = MODEL_KWARGS_NOT_USED_REGEX.search(str(e))
            if isinstance(e, BadRequestError) and match:
                unused_params = [kwarg.strip("' ") for kwarg in match.group(1).split(",")]
                _set_unsupported_text_generation_kwargs(model, unused_params)
                return self.text_generation(  # type: ignore
                    prompt=prompt,
                    details=details,
                    stream=stream,
                    model=model_id,
                    adapter_id=adapter_id,
                    best_of=best_of,
                    decoder_input_details=decoder_input_details,
                    do_sample=do_sample,
                    frequency_penalty=frequency_penalty,
                    grammar=grammar,
                    max_new_tokens=max_new_tokens,
                    repetition_penalty=repetition_penalty,
                    return_full_text=return_full_text,
                    seed=seed,
                    stop=stop,
                    temperature=temperature,
                    top_k=top_k,
                    top_n_tokens=top_n_tokens,
                    top_p=top_p,
                    truncate=truncate,
                    typical_p=typical_p,
                    watermark=watermark,
                )
            raise_text_generation_error(e)

        # Parse output
        if stream:
            return _stream_text_generation_response(bytes_output, details)  # type: ignore

        data = _bytes_to_dict(bytes_output)  # type: ignore[arg-type]

        # Data can be a single element (dict) or an iterable of dicts where we select the first element of.
        if isinstance(data, list):
            data = data[0]
        response = provider_helper.get_response(data, request_parameters)
        return TextGenerationOutput.parse_obj_as_instance(response) if details else response["generated_text"]

    def text_to_image(
        self,
        prompt: str,
        *,
        negative_prompt: Optional[str] = None,
        height: Optional[int] = None,
        width: Optional[int] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        model: Optional[str] = None,
        scheduler: Optional[str] = None,
        seed: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> "Image":
        """
        Generate an image based on a given text using a specified model.

        <Tip warning={true}>

        You must have `PIL` installed if you want to work with images (`pip install Pillow`).

        </Tip>

        <Tip>
        You can pass provider-specific parameters to the model by using the `extra_body` argument.
        </Tip>

        Args:
            prompt (`str`):
                The prompt to generate an image from.
            negative_prompt (`str`, *optional*):
                One prompt to guide what NOT to include in image generation.
            height (`int`, *optional*):
                The height in pixels of the output image
            width (`int`, *optional*):
                The width in pixels of the output image
            num_inference_steps (`int`, *optional*):
                The number of denoising steps. More denoising steps usually lead to a higher quality image at the
                expense of slower inference.
            guidance_scale (`float`, *optional*):
                A higher guidance scale value encourages the model to generate images closely linked to the text
                prompt, but values too high may cause saturation and other artifacts.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended text-to-image model will be used.
                Defaults to None.
            scheduler (`str`, *optional*):
                Override the scheduler with a compatible one.
            seed (`int`, *optional*):
                Seed for the random number generator.
            extra_body (`Dict[str, Any]`, *optional*):
                Additional provider-specific parameters to pass to the model. Refer to the provider's documentation
                for supported parameters.

        Returns:
            `Image`: The generated image.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()

        >>> image = client.text_to_image("An astronaut riding a horse on the moon.")
        >>> image.save("astronaut.png")

        >>> image = client.text_to_image(
        ...     "An astronaut riding a horse on the moon.",
        ...     negative_prompt="low resolution, blurry",
        ...     model="stabilityai/stable-diffusion-2-1",
        ... )
        >>> image.save("better_astronaut.png")
        ```
        Example using a third-party provider directly. Usage will be billed on your fal.ai account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="fal-ai",  # Use fal.ai provider
        ...     api_key="fal-ai-api-key",  # Pass your fal.ai API key
        ... )
        >>> image = client.text_to_image(
        ...     "A majestic lion in a fantasy forest",
        ...     model="black-forest-labs/FLUX.1-schnell",
        ... )
        >>> image.save("lion.png")
        ```

        Example using a third-party provider through Hugging Face Routing. Usage will be billed on your Hugging Face account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",  # Use replicate provider
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> image = client.text_to_image(
        ...     "An astronaut riding a horse on the moon.",
        ...     model="black-forest-labs/FLUX.1-dev",
        ... )
        >>> image.save("astronaut.png")
        ```

        Example using Replicate provider with extra parameters
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",  # Use replicate provider
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> image = client.text_to_image(
        ...     "An astronaut riding a horse on the moon.",
        ...     model="black-forest-labs/FLUX.1-schnell",
        ...     extra_body={"output_quality": 100},
        ... )
        >>> image.save("astronaut.png")
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="text-to-image", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=prompt,
            parameters={
                "negative_prompt": negative_prompt,
                "height": height,
                "width": width,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "scheduler": scheduler,
                "seed": seed,
                **(extra_body or {}),
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        response = provider_helper.get_response(response)
        return _bytes_to_image(response)

    def text_to_video(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        guidance_scale: Optional[float] = None,
        negative_prompt: Optional[List[str]] = None,
        num_frames: Optional[float] = None,
        num_inference_steps: Optional[int] = None,
        seed: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Generate a video based on a given text.

        <Tip>
        You can pass provider-specific parameters to the model by using the `extra_body` argument.
        </Tip>

        Args:
            prompt (`str`):
                The prompt to generate a video from.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended text-to-video model will be used.
                Defaults to None.
            guidance_scale (`float`, *optional*):
                A higher guidance scale value encourages the model to generate videos closely linked to the text
                prompt, but values too high may cause saturation and other artifacts.
            negative_prompt (`List[str]`, *optional*):
                One or several prompt to guide what NOT to include in video generation.
            num_frames (`float`, *optional*):
                The num_frames parameter determines how many video frames are generated.
            num_inference_steps (`int`, *optional*):
                The number of denoising steps. More denoising steps usually lead to a higher quality video at the
                expense of slower inference.
            seed (`int`, *optional*):
                Seed for the random number generator.
            extra_body (`Dict[str, Any]`, *optional*):
                Additional provider-specific parameters to pass to the model. Refer to the provider's documentation
                for supported parameters.

        Returns:
            `bytes`: The generated video.

        Example:

        Example using a third-party provider directly. Usage will be billed on your fal.ai account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="fal-ai",  # Using fal.ai provider
        ...     api_key="fal-ai-api-key",  # Pass your fal.ai API key
        ... )
        >>> video = client.text_to_video(
        ...     "A majestic lion running in a fantasy forest",
        ...     model="tencent/HunyuanVideo",
        ... )
        >>> with open("lion.mp4", "wb") as file:
        ...     file.write(video)
        ```

        Example using a third-party provider through Hugging Face Routing. Usage will be billed on your Hugging Face account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",  # Using replicate provider
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> video = client.text_to_video(
        ...     "A cat running in a park",
        ...     model="genmo/mochi-1-preview",
        ... )
        >>> with open("cat.mp4", "wb") as file:
        ...     file.write(video)
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="text-to-video", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=prompt,
            parameters={
                "guidance_scale": guidance_scale,
                "negative_prompt": negative_prompt,
                "num_frames": num_frames,
                "num_inference_steps": num_inference_steps,
                "seed": seed,
                **(extra_body or {}),
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        response = provider_helper.get_response(response, request_parameters)
        return response

    def text_to_speech(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        do_sample: Optional[bool] = None,
        early_stopping: Optional[Union[bool, "TextToSpeechEarlyStoppingEnum"]] = None,
        epsilon_cutoff: Optional[float] = None,
        eta_cutoff: Optional[float] = None,
        max_length: Optional[int] = None,
        max_new_tokens: Optional[int] = None,
        min_length: Optional[int] = None,
        min_new_tokens: Optional[int] = None,
        num_beam_groups: Optional[int] = None,
        num_beams: Optional[int] = None,
        penalty_alpha: Optional[float] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        typical_p: Optional[float] = None,
        use_cache: Optional[bool] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Synthesize an audio of a voice pronouncing a given text.

        <Tip>
        You can pass provider-specific parameters to the model by using the `extra_body` argument.
        </Tip>

        Args:
            text (`str`):
                The text to synthesize.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended text-to-speech model will be used.
                Defaults to None.
            do_sample (`bool`, *optional*):
                Whether to use sampling instead of greedy decoding when generating new tokens.
            early_stopping (`Union[bool, "TextToSpeechEarlyStoppingEnum"]`, *optional*):
                Controls the stopping condition for beam-based methods.
            epsilon_cutoff (`float`, *optional*):
                If set to float strictly between 0 and 1, only tokens with a conditional probability greater than
                epsilon_cutoff will be sampled. In the paper, suggested values range from 3e-4 to 9e-4, depending on
                the size of the model. See [Truncation Sampling as Language Model
                Desmoothing](https://hf.co/papers/2210.15191) for more details.
            eta_cutoff (`float`, *optional*):
                Eta sampling is a hybrid of locally typical sampling and epsilon sampling. If set to float strictly
                between 0 and 1, a token is only considered if it is greater than either eta_cutoff or sqrt(eta_cutoff)
                * exp(-entropy(softmax(next_token_logits))). The latter term is intuitively the expected next token
                probability, scaled by sqrt(eta_cutoff). In the paper, suggested values range from 3e-4 to 2e-3,
                depending on the size of the model. See [Truncation Sampling as Language Model
                Desmoothing](https://hf.co/papers/2210.15191) for more details.
            max_length (`int`, *optional*):
                The maximum length (in tokens) of the generated text, including the input.
            max_new_tokens (`int`, *optional*):
                The maximum number of tokens to generate. Takes precedence over max_length.
            min_length (`int`, *optional*):
                The minimum length (in tokens) of the generated text, including the input.
            min_new_tokens (`int`, *optional*):
                The minimum number of tokens to generate. Takes precedence over min_length.
            num_beam_groups (`int`, *optional*):
                Number of groups to divide num_beams into in order to ensure diversity among different groups of beams.
                See [this paper](https://hf.co/papers/1610.02424) for more details.
            num_beams (`int`, *optional*):
                Number of beams to use for beam search.
            penalty_alpha (`float`, *optional*):
                The value balances the model confidence and the degeneration penalty in contrastive search decoding.
            temperature (`float`, *optional*):
                The value used to modulate the next token probabilities.
            top_k (`int`, *optional*):
                The number of highest probability vocabulary tokens to keep for top-k-filtering.
            top_p (`float`, *optional*):
                If set to float < 1, only the smallest set of most probable tokens with probabilities that add up to
                top_p or higher are kept for generation.
            typical_p (`float`, *optional*):
                Local typicality measures how similar the conditional probability of predicting a target token next is
                to the expected conditional probability of predicting a random token next, given the partial text
                already generated. If set to float < 1, the smallest set of the most locally typical tokens with
                probabilities that add up to typical_p or higher are kept for generation. See [this
                paper](https://hf.co/papers/2202.00666) for more details.
            use_cache (`bool`, *optional*):
                Whether the model should use the past last key/values attentions to speed up decoding
            extra_body (`Dict[str, Any]`, *optional*):
                Additional provider-specific parameters to pass to the model. Refer to the provider's documentation
                for supported parameters.
        Returns:
            `bytes`: The generated audio.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from pathlib import Path
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()

        >>> audio = client.text_to_speech("Hello world")
        >>> Path("hello_world.flac").write_bytes(audio)
        ```

        Example using a third-party provider directly. Usage will be billed on your Replicate account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",
        ...     api_key="your-replicate-api-key",  # Pass your Replicate API key directly
        ... )
        >>> audio = client.text_to_speech(
        ...     text="Hello world",
        ...     model="OuteAI/OuteTTS-0.3-500M",
        ... )
        >>> Path("hello_world.flac").write_bytes(audio)
        ```

        Example using a third-party provider through Hugging Face Routing. Usage will be billed on your Hugging Face account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> audio =client.text_to_speech(
        ...     text="Hello world",
        ...     model="OuteAI/OuteTTS-0.3-500M",
        ... )
        >>> Path("hello_world.flac").write_bytes(audio)
        ```
        Example using Replicate provider with extra parameters
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",  # Use replicate provider
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> audio = client.text_to_speech(
        ...     "Hello, my name is Kororo, an awesome text-to-speech model.",
        ...     model="hexgrad/Kokoro-82M",
        ...     extra_body={"voice": "af_nicole"},
        ... )
        >>> Path("hello.flac").write_bytes(audio)
        ```

        Example music-gen using "YuE-s1-7B-anneal-en-cot" on fal.ai
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> lyrics = '''
        ... [verse]
        ... In the town where I was born
        ... Lived a man who sailed to sea
        ... And he told us of his life
        ... In the land of submarines
        ... So we sailed on to the sun
        ... 'Til we found a sea of green
        ... And we lived beneath the waves
        ... In our yellow submarine

        ... [chorus]
        ... We all live in a yellow submarine
        ... Yellow submarine, yellow submarine
        ... We all live in a yellow submarine
        ... Yellow submarine, yellow submarine
        ... '''
        >>> genres = "pavarotti-style tenor voice"
        >>> client = InferenceClient(
        ...     provider="fal-ai",
        ...     model="m-a-p/YuE-s1-7B-anneal-en-cot",
        ...     api_key=...,
        ... )
        >>> audio = client.text_to_speech(lyrics, extra_body={"genres": genres})
        >>> with open("output.mp3", "wb") as f:
        ...     f.write(audio)
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="text-to-speech", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "do_sample": do_sample,
                "early_stopping": early_stopping,
                "epsilon_cutoff": epsilon_cutoff,
                "eta_cutoff": eta_cutoff,
                "max_length": max_length,
                "max_new_tokens": max_new_tokens,
                "min_length": min_length,
                "min_new_tokens": min_new_tokens,
                "num_beam_groups": num_beam_groups,
                "num_beams": num_beams,
                "penalty_alpha": penalty_alpha,
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
                "typical_p": typical_p,
                "use_cache": use_cache,
                **(extra_body or {}),
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        response = provider_helper.get_response(response)
        return response

    def token_classification(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        aggregation_strategy: Optional["TokenClassificationAggregationStrategy"] = None,
        ignore_labels: Optional[List[str]] = None,
        stride: Optional[int] = None,
    ) -> List[TokenClassificationOutputElement]:
        """
        Perform token classification on the given text.
        Usually used for sentence parsing, either grammatical, or Named Entity Recognition (NER) to understand keywords contained within text.

        Args:
            text (`str`):
                A string to be classified.
            model (`str`, *optional*):
                The model to use for the token classification task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended token classification model will be used.
                Defaults to None.
            aggregation_strategy (`"TokenClassificationAggregationStrategy"`, *optional*):
                The strategy used to fuse tokens based on model predictions
            ignore_labels (`List[str`, *optional*):
                A list of labels to ignore
            stride (`int`, *optional*):
                The number of overlapping tokens between chunks when splitting the input text.

        Returns:
            `List[TokenClassificationOutputElement]`: List of [`TokenClassificationOutputElement`] items containing the entity group, confidence score, word, start and end index.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.token_classification("My name is Sarah Jessica Parker but you can call me Jessica")
        [
            TokenClassificationOutputElement(
                entity_group='PER',
                score=0.9971321225166321,
                word='Sarah Jessica Parker',
                start=11,
                end=31,
            ),
            TokenClassificationOutputElement(
                entity_group='PER',
                score=0.9773476123809814,
                word='Jessica',
                start=52,
                end=59,
            )
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="token-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "aggregation_strategy": aggregation_strategy,
                "ignore_labels": ignore_labels,
                "stride": stride,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return TokenClassificationOutputElement.parse_obj_as_list(response)

    def translation(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        src_lang: Optional[str] = None,
        tgt_lang: Optional[str] = None,
        clean_up_tokenization_spaces: Optional[bool] = None,
        truncation: Optional["TranslationTruncationStrategy"] = None,
        generate_parameters: Optional[Dict[str, Any]] = None,
    ) -> TranslationOutput:
        """
        Convert text from one language to another.

        Check out https://huggingface.co/tasks/translation for more information on how to choose the best model for
        your specific use case. Source and target languages usually depend on the model.
        However, it is possible to specify source and target languages for certain models. If you are working with one of these models,
        you can use `src_lang` and `tgt_lang` arguments to pass the relevant information.

        Args:
            text (`str`):
                A string to be translated.
            model (`str`, *optional*):
                The model to use for the translation task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended translation model will be used.
                Defaults to None.
            src_lang (`str`, *optional*):
                The source language of the text. Required for models that can translate from multiple languages.
            tgt_lang (`str`, *optional*):
                Target language to translate to. Required for models that can translate to multiple languages.
            clean_up_tokenization_spaces (`bool`, *optional*):
                Whether to clean up the potential extra spaces in the text output.
            truncation (`"TranslationTruncationStrategy"`, *optional*):
                The truncation strategy to use.
            generate_parameters (`Dict[str, Any]`, *optional*):
                Additional parametrization of the text generation algorithm.

        Returns:
            [`TranslationOutput`]: The generated translated text.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.
            `ValueError`:
                If only one of the `src_lang` and `tgt_lang` arguments are provided.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.translation("My name is Wolfgang and I live in Berlin")
        'Mein Name ist Wolfgang und ich lebe in Berlin.'
        >>> client.translation("My name is Wolfgang and I live in Berlin", model="Helsinki-NLP/opus-mt-en-fr")
        TranslationOutput(translation_text='Je m'appelle Wolfgang et je vis à Berlin.')
        ```

        Specifying languages:
        ```py
        >>> client.translation("My name is Sarah Jessica Parker but you can call me Jessica", model="facebook/mbart-large-50-many-to-many-mmt", src_lang="en_XX", tgt_lang="fr_XX")
        "Mon nom est Sarah Jessica Parker mais vous pouvez m'appeler Jessica"
        ```
        """
        # Throw error if only one of `src_lang` and `tgt_lang` was given
        if src_lang is not None and tgt_lang is None:
            raise ValueError("You cannot specify `src_lang` without specifying `tgt_lang`.")

        if src_lang is None and tgt_lang is not None:
            raise ValueError("You cannot specify `tgt_lang` without specifying `src_lang`.")

        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="translation", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "src_lang": src_lang,
                "tgt_lang": tgt_lang,
                "clean_up_tokenization_spaces": clean_up_tokenization_spaces,
                "truncation": truncation,
                "generate_parameters": generate_parameters,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return TranslationOutput.parse_obj_as_list(response)[0]

    def visual_question_answering(
        self,
        image: ContentT,
        question: str,
        *,
        model: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[VisualQuestionAnsweringOutputElement]:
        """
        Answering open-ended questions based on an image.

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The input image for the context. It can be raw bytes, an image file, or a URL to an online image.
            question (`str`):
                Question to be answered.
            model (`str`, *optional*):
                The model to use for the visual question answering task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended visual question answering model will be used.
                Defaults to None.
            top_k (`int`, *optional*):
                The number of answers to return (will be chosen by order of likelihood). Note that we return less than
                topk answers if there are not enough options available within the context.
        Returns:
            `List[VisualQuestionAnsweringOutputElement]`: a list of [`VisualQuestionAnsweringOutputElement`] items containing the predicted label and associated probability.

        Raises:
            `InferenceTimeoutError`:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.visual_question_answering(
        ...     image="https://huggingface.co/datasets/mishig/sample_images/resolve/main/tiger.jpg",
        ...     question="What is the animal doing?"
        ... )
        [
            VisualQuestionAnsweringOutputElement(score=0.778609573841095, answer='laying down'),
            VisualQuestionAnsweringOutputElement(score=0.6957435607910156, answer='sitting'),
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="visual-question-answering", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={"top_k": top_k},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
            extra_payload={"question": question, "image": _b64_encode(image)},
        )
        response = self._inner_post(request_parameters)
        return VisualQuestionAnsweringOutputElement.parse_obj_as_list(response)

    def zero_shot_classification(
        self,
        text: str,
        candidate_labels: List[str],
        *,
        multi_label: Optional[bool] = False,
        hypothesis_template: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[ZeroShotClassificationOutputElement]:
        """
        Provide as input a text and a set of candidate labels to classify the input text.

        Args:
            text (`str`):
                The input text to classify.
            candidate_labels (`List[str]`):
                The set of possible class labels to classify the text into.
            labels (`List[str]`, *optional*):
                (deprecated) List of strings. Each string is the verbalization of a possible label for the input text.
            multi_label (`bool`, *optional*):
                Whether multiple candidate labels can be true. If false, the scores are normalized such that the sum of
                the label likelihoods for each sequence is 1. If true, the labels are considered independent and
                probabilities are normalized for each candidate.
            hypothesis_template (`str`, *optional*):
                The sentence used in conjunction with `candidate_labels` to attempt the text classification by
                replacing the placeholder with the candidate labels.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. If not provided, the default recommended zero-shot classification model will be used.


        Returns:
            `List[ZeroShotClassificationOutputElement]`: List of [`ZeroShotClassificationOutputElement`] items containing the predicted labels and their confidence.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example with `multi_label=False`:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> text = (
        ...     "A new model offers an explanation for how the Galilean satellites formed around the solar system's"
        ...     "largest world. Konstantin Batygin did not set out to solve one of the solar system's most puzzling"
        ...     " mysteries when he went for a run up a hill in Nice, France."
        ... )
        >>> labels = ["space & cosmos", "scientific discovery", "microbiology", "robots", "archeology"]
        >>> client.zero_shot_classification(text, labels)
        [
            ZeroShotClassificationOutputElement(label='scientific discovery', score=0.7961668968200684),
            ZeroShotClassificationOutputElement(label='space & cosmos', score=0.18570658564567566),
            ZeroShotClassificationOutputElement(label='microbiology', score=0.00730885099619627),
            ZeroShotClassificationOutputElement(label='archeology', score=0.006258360575884581),
            ZeroShotClassificationOutputElement(label='robots', score=0.004559356719255447),
        ]
        >>> client.zero_shot_classification(text, labels, multi_label=True)
        [
            ZeroShotClassificationOutputElement(label='scientific discovery', score=0.9829297661781311),
            ZeroShotClassificationOutputElement(label='space & cosmos', score=0.755190908908844),
            ZeroShotClassificationOutputElement(label='microbiology', score=0.0005462635890580714),
            ZeroShotClassificationOutputElement(label='archeology', score=0.00047131875180639327),
            ZeroShotClassificationOutputElement(label='robots', score=0.00030448526376858354),
        ]
        ```

        Example with `multi_label=True` and a custom `hypothesis_template`:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.zero_shot_classification(
        ...    text="I really like our dinner and I'm very happy. I don't like the weather though.",
        ...    labels=["positive", "negative", "pessimistic", "optimistic"],
        ...    multi_label=True,
        ...    hypothesis_template="This text is {} towards the weather"
        ... )
        [
            ZeroShotClassificationOutputElement(label='negative', score=0.9231801629066467),
            ZeroShotClassificationOutputElement(label='pessimistic', score=0.8760990500450134),
            ZeroShotClassificationOutputElement(label='optimistic', score=0.0008674879791215062),
            ZeroShotClassificationOutputElement(label='positive', score=0.0005250611575320363)
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="zero-shot-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "candidate_labels": candidate_labels,
                "multi_label": multi_label,
                "hypothesis_template": hypothesis_template,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        output = _bytes_to_dict(response)
        return [
            ZeroShotClassificationOutputElement.parse_obj_as_instance({"label": label, "score": score})
            for label, score in zip(output["labels"], output["scores"])
        ]

    def zero_shot_image_classification(
        self,
        image: ContentT,
        candidate_labels: List[str],
        *,
        model: Optional[str] = None,
        hypothesis_template: Optional[str] = None,
        # deprecated argument
        labels: List[str] = None,  # type: ignore
    ) -> List[ZeroShotImageClassificationOutputElement]:
        """
        Provide input image and text labels to predict text labels for the image.

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The input image to caption. It can be raw bytes, an image file, or a URL to an online image.
            candidate_labels (`List[str]`):
                The candidate labels for this image
            labels (`List[str]`, *optional*):
                (deprecated) List of string possible labels. There must be at least 2 labels.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. If not provided, the default recommended zero-shot image classification model will be used.
            hypothesis_template (`str`, *optional*):
                The sentence used in conjunction with `candidate_labels` to attempt the image classification by
                replacing the placeholder with the candidate labels.

        Returns:
            `List[ZeroShotImageClassificationOutputElement]`: List of [`ZeroShotImageClassificationOutputElement`] items containing the predicted labels and their confidence.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `HTTPError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()

        >>> client.zero_shot_image_classification(
        ...     "https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Cute_dog.jpg/320px-Cute_dog.jpg",
        ...     labels=["dog", "cat", "horse"],
        ... )
        [ZeroShotImageClassificationOutputElement(label='dog', score=0.956),...]
        ```
        """
        # Raise ValueError if input is less than 2 labels
        if len(candidate_labels) < 2:
            raise ValueError("You must specify at least 2 classes to compare.")

        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="zero-shot-image-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={
                "candidate_labels": candidate_labels,
                "hypothesis_template": hypothesis_template,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = self._inner_post(request_parameters)
        return ZeroShotImageClassificationOutputElement.parse_obj_as_list(response)

    @_deprecate_method(
        version="0.35.0",
        message=(
            "HF Inference API is getting revamped and will only support warm models in the future (no cold start allowed)."
            " Use `HfApi.list_models(..., inference_provider='...')` to list warm models per provider."
        ),
    )
    def list_deployed_models(
        self, frameworks: Union[None, str, Literal["all"], List[str]] = None
    ) -> Dict[str, List[str]]:
        """
        List models deployed on the HF Serverless Inference API service.

        This helper checks deployed models framework by framework. By default, it will check the 4 main frameworks that
        are supported and account for 95% of the hosted models. However, if you want a complete list of models you can
        specify `frameworks="all"` as input. Alternatively, if you know before-hand which framework you are interested
        in, you can also restrict to search to this one (e.g. `frameworks="text-generation-inference"`). The more
        frameworks are checked, the more time it will take.

        <Tip warning={true}>

        This endpoint method does not return a live list of all models available for the HF Inference API service.
        It searches over a cached list of models that were recently available and the list may not be up to date.
        If you want to know the live status of a specific model, use [`~InferenceClient.get_model_status`].

        </Tip>

        <Tip>

        This endpoint method is mostly useful for discoverability. If you already know which model you want to use and want to
        check its availability, you can directly use [`~InferenceClient.get_model_status`].

        </Tip>

        Args:
            frameworks (`Literal["all"]` or `List[str]` or `str`, *optional*):
                The frameworks to filter on. By default only a subset of the available frameworks are tested. If set to
                "all", all available frameworks will be tested. It is also possible to provide a single framework or a
                custom set of frameworks to check.

        Returns:
            `Dict[str, List[str]]`: A dictionary mapping task names to a sorted list of model IDs.

        Example:
        ```python
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()

        # Discover zero-shot-classification models currently deployed
        >>> models = client.list_deployed_models()
        >>> models["zero-shot-classification"]
        ['Narsil/deberta-large-mnli-zero-cls', 'facebook/bart-large-mnli', ...]

        # List from only 1 framework
        >>> client.list_deployed_models("text-generation-inference")
        {'text-generation': ['bigcode/starcoder', 'meta-llama/Llama-2-70b-chat-hf', ...], ...}
        ```
        """
        if self.provider != "hf-inference":
            raise ValueError(f"Listing deployed models is not supported on '{self.provider}'.")

        # Resolve which frameworks to check
        if frameworks is None:
            frameworks = constants.MAIN_INFERENCE_API_FRAMEWORKS
        elif frameworks == "all":
            frameworks = constants.ALL_INFERENCE_API_FRAMEWORKS
        elif isinstance(frameworks, str):
            frameworks = [frameworks]
        frameworks = list(set(frameworks))

        # Fetch them iteratively
        models_by_task: Dict[str, List[str]] = {}

        def _unpack_response(framework: str, items: List[Dict]) -> None:
            for model in items:
                if framework == "sentence-transformers":
                    # Model running with the `sentence-transformers` framework can work with both tasks even if not
                    # branded as such in the API response
                    models_by_task.setdefault("feature-extraction", []).append(model["model_id"])
                    models_by_task.setdefault("sentence-similarity", []).append(model["model_id"])
                else:
                    models_by_task.setdefault(model["task"], []).append(model["model_id"])

        for framework in frameworks:
            response = get_session().get(
                f"{constants.INFERENCE_ENDPOINT}/framework/{framework}", headers=build_hf_headers(token=self.token)
            )
            hf_raise_for_status(response)
            _unpack_response(framework, response.json())

        # Sort alphabetically for discoverability and return
        for task, models in models_by_task.items():
            models_by_task[task] = sorted(set(models), key=lambda x: x.lower())
        return models_by_task

    def get_endpoint_info(self, *, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about the deployed endpoint.

        This endpoint is only available on endpoints powered by Text-Generation-Inference (TGI) or Text-Embedding-Inference (TEI).
        Endpoints powered by `transformers` return an empty payload.

        Args:
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. Defaults to None.

        Returns:
            `Dict[str, Any]`: Information about the endpoint.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient("meta-llama/Meta-Llama-3-70B-Instruct")
        >>> client.get_endpoint_info()
        {
            'model_id': 'meta-llama/Meta-Llama-3-70B-Instruct',
            'model_sha': None,
            'model_dtype': 'torch.float16',
            'model_device_type': 'cuda',
            'model_pipeline_tag': None,
            'max_concurrent_requests': 128,
            'max_best_of': 2,
            'max_stop_sequences': 4,
            'max_input_length': 8191,
            'max_total_tokens': 8192,
            'waiting_served_ratio': 0.3,
            'max_batch_total_tokens': 1259392,
            'max_waiting_tokens': 20,
            'max_batch_size': None,
            'validation_workers': 32,
            'max_client_batch_size': 4,
            'version': '2.0.2',
            'sha': 'dccab72549635c7eb5ddb17f43f0b7cdff07c214',
            'docker_label': 'sha-dccab72'
        }
        ```
        """
        if self.provider != "hf-inference":
            raise ValueError(f"Getting endpoint info is not supported on '{self.provider}'.")

        model = model or self.model
        if model is None:
            raise ValueError("Model id not provided.")
        if model.startswith(("http://", "https://")):
            url = model.rstrip("/") + "/info"
        else:
            url = f"{constants.INFERENCE_ENDPOINT}/models/{model}/info"

        response = get_session().get(url, headers=build_hf_headers(token=self.token))
        hf_raise_for_status(response)
        return response.json()

    def health_check(self, model: Optional[str] = None) -> bool:
        """
        Check the health of the deployed endpoint.

        Health check is only available with Inference Endpoints powered by Text-Generation-Inference (TGI) or Text-Embedding-Inference (TEI).
        For Inference API, please use [`InferenceClient.get_model_status`] instead.

        Args:
            model (`str`, *optional*):
                URL of the Inference Endpoint. This parameter overrides the model defined at the instance level. Defaults to None.

        Returns:
            `bool`: True if everything is working fine.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient("https://jzgu0buei5.us-east-1.aws.endpoints.huggingface.cloud")
        >>> client.health_check()
        True
        ```
        """
        if self.provider != "hf-inference":
            raise ValueError(f"Health check is not supported on '{self.provider}'.")

        model = model or self.model
        if model is None:
            raise ValueError("Model id not provided.")
        if not model.startswith(("http://", "https://")):
            raise ValueError(
                "Model must be an Inference Endpoint URL. For serverless Inference API, please use `InferenceClient.get_model_status`."
            )
        url = model.rstrip("/") + "/health"

        response = get_session().get(url, headers=build_hf_headers(token=self.token))
        return response.status_code == 200

    @_deprecate_method(
        version="0.35.0",
        message=(
            "HF Inference API is getting revamped and will only support warm models in the future (no cold start allowed)."
            " Use `HfApi.model_info` to get the model status both with HF Inference API and external providers."
        ),
    )
    def get_model_status(self, model: Optional[str] = None) -> ModelStatus:
        """
        Get the status of a model hosted on the HF Inference API.

        <Tip>

        This endpoint is mostly useful when you already know which model you want to use and want to check its
        availability. If you want to discover already deployed models, you should rather use [`~InferenceClient.list_deployed_models`].

        </Tip>

        Args:
            model (`str`, *optional*):
                Identifier of the model for witch the status gonna be checked. If model is not provided,
                the model associated with this instance of [`InferenceClient`] will be used. Only HF Inference API service can be checked so the
                identifier cannot be a URL.


        Returns:
            [`ModelStatus`]: An instance of ModelStatus dataclass, containing information,
                         about the state of the model: load, state, compute type and framework.

        Example:
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient()
        >>> client.get_model_status("meta-llama/Meta-Llama-3-8B-Instruct")
        ModelStatus(loaded=True, state='Loaded', compute_type='gpu', framework='text-generation-inference')
        ```
        """
        if self.provider != "hf-inference":
            raise ValueError(f"Getting model status is not supported on '{self.provider}'.")

        model = model or self.model
        if model is None:
            raise ValueError("Model id not provided.")
        if model.startswith("https://"):
            raise NotImplementedError("Model status is only available for Inference API endpoints.")
        url = f"{constants.INFERENCE_ENDPOINT}/status/{model}"

        response = get_session().get(url, headers=build_hf_headers(token=self.token))
        hf_raise_for_status(response)
        response_data = response.json()

        if "error" in response_data:
            raise ValueError(response_data["error"])

        return ModelStatus(
            loaded=response_data["loaded"],
            state=response_data["state"],
            compute_type=response_data["compute_type"],
            framework=response_data["framework"],
        )

    @property
    def chat(self) -> "ProxyClientChat":
        return ProxyClientChat(self)


class _ProxyClient:
    """Proxy class to be able to call `client.chat.completion.create(...)` as OpenAI client."""

    def __init__(self, client: InferenceClient):
        self._client = client


class ProxyClientChat(_ProxyClient):
    """Proxy class to be able to call `client.chat.completion.create(...)` as OpenAI client."""

    @property
    def completions(self) -> "ProxyClientChatCompletions":
        return ProxyClientChatCompletions(self._client)


class ProxyClientChatCompletions(_ProxyClient):
    """Proxy class to be able to call `client.chat.completion.create(...)` as OpenAI client."""

    @property
    def create(self):
        return self._client.chat_completion

# === NexusCore/openenv\Lib\site-packages\fontTools\otlLib\builder.py ===
from __future__ import annotations

from collections import namedtuple, OrderedDict
import itertools
from typing import Dict, Union
from fontTools.misc.fixedTools import fixedToFloat
from fontTools.misc.roundTools import otRound
from fontTools import ttLib
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables.otBase import (
    ValueRecord,
    valueRecordFormatDict,
    OTLOffsetOverflowError,
    OTTableWriter,
)
from fontTools.ttLib.ttFont import TTFont
from fontTools.feaLib.ast import STATNameStatement
from fontTools.otlLib.optimize.gpos import (
    _compression_level_from_env,
    compact_lookup,
)
from fontTools.otlLib.error import OpenTypeLibError
from fontTools.misc.loggingTools import deprecateFunction
from functools import reduce
import logging
import copy


log = logging.getLogger(__name__)


def buildCoverage(glyphs, glyphMap):
    """Builds a coverage table.

    Coverage tables (as defined in the `OpenType spec <https://docs.microsoft.com/en-gb/typography/opentype/spec/chapter2#coverage-table>`__)
    are used in all OpenType Layout lookups apart from the Extension type, and
    define the glyphs involved in a layout subtable. This allows shaping engines
    to compare the glyph stream with the coverage table and quickly determine
    whether a subtable should be involved in a shaping operation.

    This function takes a list of glyphs and a glyphname-to-ID map, and
    returns a ``Coverage`` object representing the coverage table.

    Example::

        glyphMap = font.getReverseGlyphMap()
        glyphs = [ "A", "B", "C" ]
        coverage = buildCoverage(glyphs, glyphMap)

    Args:
        glyphs: a sequence of glyph names.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns:
        An ``otTables.Coverage`` object or ``None`` if there are no glyphs
        supplied.
    """

    if not glyphs:
        return None
    self = ot.Coverage()
    try:
        self.glyphs = sorted(set(glyphs), key=glyphMap.__getitem__)
    except KeyError as e:
        raise ValueError(f"Could not find glyph {e} in font") from e

    return self


LOOKUP_FLAG_RIGHT_TO_LEFT = 0x0001
LOOKUP_FLAG_IGNORE_BASE_GLYPHS = 0x0002
LOOKUP_FLAG_IGNORE_LIGATURES = 0x0004
LOOKUP_FLAG_IGNORE_MARKS = 0x0008
LOOKUP_FLAG_USE_MARK_FILTERING_SET = 0x0010


def buildLookup(subtables, flags=0, markFilterSet=None, table=None, extension=False):
    """Turns a collection of rules into a lookup.

    A Lookup (as defined in the `OpenType Spec <https://docs.microsoft.com/en-gb/typography/opentype/spec/chapter2#lookupTbl>`__)
    wraps the individual rules in a layout operation (substitution or
    positioning) in a data structure expressing their overall lookup type -
    for example, single substitution, mark-to-base attachment, and so on -
    as well as the lookup flags and any mark filtering sets. You may import
    the following constants to express lookup flags:

    - ``LOOKUP_FLAG_RIGHT_TO_LEFT``
    - ``LOOKUP_FLAG_IGNORE_BASE_GLYPHS``
    - ``LOOKUP_FLAG_IGNORE_LIGATURES``
    - ``LOOKUP_FLAG_IGNORE_MARKS``
    - ``LOOKUP_FLAG_USE_MARK_FILTERING_SET``

    Args:
        subtables: A list of layout subtable objects (e.g.
            ``MultipleSubst``, ``PairPos``, etc.) or ``None``.
        flags (int): This lookup's flags.
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
        table (str): The name of the table this lookup belongs to, e.g. "GPOS" or "GSUB".
        extension (bool): ``True`` if this is an extension lookup, ``False`` otherwise.

    Returns:
        An ``otTables.Lookup`` object or ``None`` if there are no subtables
        supplied.
    """
    if subtables is None:
        return None
    subtables = [st for st in subtables if st is not None]
    if not subtables:
        return None
    assert all(
        t.LookupType == subtables[0].LookupType for t in subtables
    ), "all subtables must have the same LookupType; got %s" % repr(
        [t.LookupType for t in subtables]
    )

    if extension:
        assert table in ("GPOS", "GSUB")
        lookupType = 7 if table == "GSUB" else 9
        extSubTableClass = ot.lookupTypes[table][lookupType]
        for i, st in enumerate(subtables):
            subtables[i] = extSubTableClass()
            subtables[i].Format = 1
            subtables[i].ExtSubTable = st
            subtables[i].ExtensionLookupType = st.LookupType
    else:
        lookupType = subtables[0].LookupType

    self = ot.Lookup()
    self.LookupType = lookupType
    self.LookupFlag = flags
    self.SubTable = subtables
    self.SubTableCount = len(self.SubTable)
    if markFilterSet is not None:
        self.LookupFlag |= LOOKUP_FLAG_USE_MARK_FILTERING_SET
        assert isinstance(markFilterSet, int), markFilterSet
        self.MarkFilteringSet = markFilterSet
    else:
        assert (self.LookupFlag & LOOKUP_FLAG_USE_MARK_FILTERING_SET) == 0, (
            "if markFilterSet is None, flags must not set "
            "LOOKUP_FLAG_USE_MARK_FILTERING_SET; flags=0x%04x" % flags
        )
    return self


class LookupBuilder(object):
    SUBTABLE_BREAK_ = "SUBTABLE_BREAK"

    def __init__(self, font, location, table, lookup_type, extension=False):
        self.font = font
        self.glyphMap = font.getReverseGlyphMap()
        self.location = location
        self.table, self.lookup_type = table, lookup_type
        self.lookupflag = 0
        self.markFilterSet = None
        self.lookup_index = None  # assigned when making final tables
        self.extension = extension
        assert table in ("GPOS", "GSUB")

    def equals(self, other):
        return (
            isinstance(other, self.__class__)
            and self.table == other.table
            and self.lookupflag == other.lookupflag
            and self.markFilterSet == other.markFilterSet
            and self.extension == other.extension
        )

    def promote_lookup_type(self, is_named_lookup):
        return [self]

    def inferGlyphClasses(self):
        """Infers glyph glasses for the GDEF table, such as {"cedilla":3}."""
        return {}

    def getAlternateGlyphs(self):
        """Helper for building 'aalt' features."""
        return {}

    def buildLookup_(self, subtables):
        return buildLookup(
            subtables,
            self.lookupflag,
            self.markFilterSet,
            self.table,
            self.extension,
        )

    def buildMarkClasses_(self, marks):
        """{"cedilla": ("BOTTOM", ast.Anchor), ...} --> {"BOTTOM":0, "TOP":1}

        Helper for MarkBasePostBuilder, MarkLigPosBuilder, and
        MarkMarkPosBuilder. Seems to return the same numeric IDs
        for mark classes as the AFDKO makeotf tool.
        """
        ids = {}
        for mark in sorted(marks.keys(), key=self.font.getGlyphID):
            markClassName, _markAnchor = marks[mark]
            if markClassName not in ids:
                ids[markClassName] = len(ids)
        return ids

    def setBacktrackCoverage_(self, prefix, subtable):
        subtable.BacktrackGlyphCount = len(prefix)
        subtable.BacktrackCoverage = []
        for p in reversed(prefix):
            coverage = buildCoverage(p, self.glyphMap)
            subtable.BacktrackCoverage.append(coverage)

    def setLookAheadCoverage_(self, suffix, subtable):
        subtable.LookAheadGlyphCount = len(suffix)
        subtable.LookAheadCoverage = []
        for s in suffix:
            coverage = buildCoverage(s, self.glyphMap)
            subtable.LookAheadCoverage.append(coverage)

    def setInputCoverage_(self, glyphs, subtable):
        subtable.InputGlyphCount = len(glyphs)
        subtable.InputCoverage = []
        for g in glyphs:
            coverage = buildCoverage(g, self.glyphMap)
            subtable.InputCoverage.append(coverage)

    def setCoverage_(self, glyphs, subtable):
        subtable.GlyphCount = len(glyphs)
        subtable.Coverage = []
        for g in glyphs:
            coverage = buildCoverage(g, self.glyphMap)
            subtable.Coverage.append(coverage)

    def build_subst_subtables(self, mapping, klass):
        substitutions = [{}]
        for key in mapping:
            if key[0] == self.SUBTABLE_BREAK_:
                substitutions.append({})
            else:
                substitutions[-1][key] = mapping[key]
        subtables = [klass(s) for s in substitutions]
        return subtables

    def add_subtable_break(self, location):
        """Add an explicit subtable break.

        Args:
            location: A string or tuple representing the location in the
                original source which produced this break, or ``None`` if
                no location is provided.
        """
        log.warning(
            OpenTypeLibError(
                'unsupported "subtable" statement for lookup type', location
            )
        )


class AlternateSubstBuilder(LookupBuilder):
    """Builds an Alternate Substitution (GSUB3) lookup.

    Users are expected to manually add alternate glyph substitutions to
    the ``alternates`` attribute after the object has been initialized,
    e.g.::

        builder.alternates["A"] = ["A.alt1", "A.alt2"]

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        alternates: An ordered dictionary of alternates, mapping glyph names
            to a list of names of alternates.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GSUB", 3)
        self.alternates = OrderedDict()

    def equals(self, other):
        return LookupBuilder.equals(self, other) and self.alternates == other.alternates

    def build(self):
        """Build the lookup.

        Returns:
            An ``otTables.Lookup`` object representing the alternate
            substitution lookup.
        """
        subtables = self.build_subst_subtables(
            self.alternates, buildAlternateSubstSubtable
        )
        return self.buildLookup_(subtables)

    def getAlternateGlyphs(self):
        return self.alternates

    def add_subtable_break(self, location):
        self.alternates[(self.SUBTABLE_BREAK_, location)] = self.SUBTABLE_BREAK_


class ChainContextualRule(
    namedtuple("ChainContextualRule", ["prefix", "glyphs", "suffix", "lookups"])
):
    @property
    def is_subtable_break(self):
        return self.prefix == LookupBuilder.SUBTABLE_BREAK_


class ChainContextualRuleset:
    def __init__(self):
        self.rules = []

    def addRule(self, rule):
        self.rules.append(rule)

    @property
    def hasPrefixOrSuffix(self):
        # Do we have any prefixes/suffixes? If this is False for all
        # rulesets, we can express the whole lookup as GPOS5/GSUB7.
        for rule in self.rules:
            if len(rule.prefix) > 0 or len(rule.suffix) > 0:
                return True
        return False

    @property
    def hasAnyGlyphClasses(self):
        # Do we use glyph classes anywhere in the rules? If this is False
        # we can express this subtable as a Format 1.
        for rule in self.rules:
            for coverage in (rule.prefix, rule.glyphs, rule.suffix):
                if any(len(x) > 1 for x in coverage):
                    return True
        return False

    def format2ClassDefs(self):
        PREFIX, GLYPHS, SUFFIX = 0, 1, 2
        classDefBuilders = []
        for ix in [PREFIX, GLYPHS, SUFFIX]:
            context = []
            for r in self.rules:
                context.append(r[ix])
            classes = self._classBuilderForContext(context)
            if not classes:
                return None
            classDefBuilders.append(classes)
        return classDefBuilders

    def _classBuilderForContext(self, context):
        classdefbuilder = ClassDefBuilder(useClass0=False)
        for position in context:
            for glyphset in position:
                glyphs = set(glyphset)
                if not classdefbuilder.canAdd(glyphs):
                    return None
                classdefbuilder.add(glyphs)
        return classdefbuilder


class ChainContextualBuilder(LookupBuilder):
    def equals(self, other):
        return LookupBuilder.equals(self, other) and self.rules == other.rules

    def rulesets(self):
        # Return a list of ChainContextRuleset objects, taking explicit
        # subtable breaks into account
        ruleset = [ChainContextualRuleset()]
        for rule in self.rules:
            if rule.is_subtable_break:
                ruleset.append(ChainContextualRuleset())
                continue
            ruleset[-1].addRule(rule)
        # Squish any empty subtables
        return [x for x in ruleset if len(x.rules) > 0]

    def getCompiledSize_(self, subtables):
        if not subtables:
            return 0
        # We need to make a copy here because compiling
        # modifies the subtable (finalizing formats etc.)
        table = self.buildLookup_(copy.deepcopy(subtables))
        w = OTTableWriter()
        table.compile(w, self.font)
        size = len(w.getAllData())
        return size

    def build(self):
        """Build the lookup.

        Returns:
            An ``otTables.Lookup`` object representing the chained
            contextual positioning lookup.
        """
        subtables = []

        rulesets = self.rulesets()
        chaining = any(ruleset.hasPrefixOrSuffix for ruleset in rulesets)

        # https://github.com/fonttools/fonttools/issues/2539
        #
        # Unfortunately, as of 2022-03-07, Apple's CoreText renderer does not
        # correctly process GPOS7 lookups, so for now we force contextual
        # positioning lookups to be chaining (GPOS8).
        #
        # This seems to be fixed as of macOS 13.2, but we keep disabling this
        # for now until we are no longer concerned about old macOS versions.
        # But we allow people to opt-out of this with the config key below.
        write_gpos7 = self.font.cfg.get("fontTools.otlLib.builder:WRITE_GPOS7")
        # horrible separation of concerns breach
        if not write_gpos7 and self.subtable_type == "Pos":
            chaining = True

        for ruleset in rulesets:
            # Determine format strategy. We try to build formats 1, 2 and 3
            # subtables and then work out which is best. candidates list holds
            # the subtables in each format for this ruleset (including a dummy
            # "format 0" to make the addressing match the format numbers).

            # We can always build a format 3 lookup by accumulating each of
            # the rules into a list, so start with that.
            candidates = [None, None, None, []]
            for rule in ruleset.rules:
                candidates[3].append(self.buildFormat3Subtable(rule, chaining))

            # Can we express the whole ruleset as a format 2 subtable?
            classdefs = ruleset.format2ClassDefs()
            if classdefs:
                candidates[2] = [
                    self.buildFormat2Subtable(ruleset, classdefs, chaining)
                ]

            if not ruleset.hasAnyGlyphClasses:
                candidates[1] = [self.buildFormat1Subtable(ruleset, chaining)]

            candidates_by_size = []
            for i in [1, 2, 3]:
                if candidates[i]:
                    try:
                        size = self.getCompiledSize_(candidates[i])
                    except OTLOffsetOverflowError as e:
                        log.warning(
                            "Contextual format %i at %s overflowed (%s)"
                            % (i, str(self.location), e)
                        )
                    else:
                        candidates_by_size.append((size, candidates[i]))

            if not candidates_by_size:
                raise OpenTypeLibError("All candidates overflowed", self.location)

            _min_size, winner = min(candidates_by_size, key=lambda x: x[0])
            subtables.extend(winner)

        # If we are not chaining, lookup type will be automatically fixed by
        # buildLookup_
        return self.buildLookup_(subtables)

    def buildFormat1Subtable(self, ruleset, chaining=True):
        st = self.newSubtable_(chaining=chaining)
        st.Format = 1
        st.populateDefaults()
        coverage = set()
        rulesetsByFirstGlyph = {}
        ruleAttr = self.ruleAttr_(format=1, chaining=chaining)

        for rule in ruleset.rules:
            ruleAsSubtable = self.newRule_(format=1, chaining=chaining)

            if chaining:
                ruleAsSubtable.BacktrackGlyphCount = len(rule.prefix)
                ruleAsSubtable.LookAheadGlyphCount = len(rule.suffix)
                ruleAsSubtable.Backtrack = [list(x)[0] for x in reversed(rule.prefix)]
                ruleAsSubtable.LookAhead = [list(x)[0] for x in rule.suffix]

                ruleAsSubtable.InputGlyphCount = len(rule.glyphs)
            else:
                ruleAsSubtable.GlyphCount = len(rule.glyphs)

            ruleAsSubtable.Input = [list(x)[0] for x in rule.glyphs[1:]]

            self.buildLookupList(rule, ruleAsSubtable)

            firstGlyph = list(rule.glyphs[0])[0]
            if firstGlyph not in rulesetsByFirstGlyph:
                coverage.add(firstGlyph)
                rulesetsByFirstGlyph[firstGlyph] = []
            rulesetsByFirstGlyph[firstGlyph].append(ruleAsSubtable)

        st.Coverage = buildCoverage(coverage, self.glyphMap)
        ruleSets = []
        for g in st.Coverage.glyphs:
            ruleSet = self.newRuleSet_(format=1, chaining=chaining)
            setattr(ruleSet, ruleAttr, rulesetsByFirstGlyph[g])
            setattr(ruleSet, f"{ruleAttr}Count", len(rulesetsByFirstGlyph[g]))
            ruleSets.append(ruleSet)

        setattr(st, self.ruleSetAttr_(format=1, chaining=chaining), ruleSets)
        setattr(
            st, self.ruleSetAttr_(format=1, chaining=chaining) + "Count", len(ruleSets)
        )

        return st

    def buildFormat2Subtable(self, ruleset, classdefs, chaining=True):
        st = self.newSubtable_(chaining=chaining)
        st.Format = 2
        st.populateDefaults()

        if chaining:
            (
                st.BacktrackClassDef,
                st.InputClassDef,
                st.LookAheadClassDef,
            ) = [c.build() for c in classdefs]
        else:
            st.ClassDef = classdefs[1].build()

        inClasses = classdefs[1].classes()

        classSets = []
        for _ in inClasses:
            classSet = self.newRuleSet_(format=2, chaining=chaining)
            classSets.append(classSet)

        coverage = set()
        classRuleAttr = self.ruleAttr_(format=2, chaining=chaining)

        for rule in ruleset.rules:
            ruleAsSubtable = self.newRule_(format=2, chaining=chaining)
            if chaining:
                ruleAsSubtable.BacktrackGlyphCount = len(rule.prefix)
                ruleAsSubtable.LookAheadGlyphCount = len(rule.suffix)
                # The glyphs in the rule may be list, tuple, odict_keys...
                # Order is not important anyway because they are guaranteed
                # to be members of the same class.
                ruleAsSubtable.Backtrack = [
                    st.BacktrackClassDef.classDefs[list(x)[0]]
                    for x in reversed(rule.prefix)
                ]
                ruleAsSubtable.LookAhead = [
                    st.LookAheadClassDef.classDefs[list(x)[0]] for x in rule.suffix
                ]

                ruleAsSubtable.InputGlyphCount = len(rule.glyphs)
                ruleAsSubtable.Input = [
                    st.InputClassDef.classDefs[list(x)[0]] for x in rule.glyphs[1:]
                ]
                setForThisRule = classSets[
                    st.InputClassDef.classDefs[list(rule.glyphs[0])[0]]
                ]
            else:
                ruleAsSubtable.GlyphCount = len(rule.glyphs)
                ruleAsSubtable.Class = [  # The spec calls this InputSequence
                    st.ClassDef.classDefs[list(x)[0]] for x in rule.glyphs[1:]
                ]
                setForThisRule = classSets[
                    st.ClassDef.classDefs[list(rule.glyphs[0])[0]]
                ]

            self.buildLookupList(rule, ruleAsSubtable)
            coverage |= set(rule.glyphs[0])

            getattr(setForThisRule, classRuleAttr).append(ruleAsSubtable)
            setattr(
                setForThisRule,
                f"{classRuleAttr}Count",
                getattr(setForThisRule, f"{classRuleAttr}Count") + 1,
            )
        for i, classSet in enumerate(classSets):
            if not getattr(classSet, classRuleAttr):
                # class sets can be null so replace nop sets with None
                classSets[i] = None
        setattr(st, self.ruleSetAttr_(format=2, chaining=chaining), classSets)
        setattr(
            st, self.ruleSetAttr_(format=2, chaining=chaining) + "Count", len(classSets)
        )
        st.Coverage = buildCoverage(coverage, self.glyphMap)
        return st

    def buildFormat3Subtable(self, rule, chaining=True):
        st = self.newSubtable_(chaining=chaining)
        st.Format = 3
        if chaining:
            self.setBacktrackCoverage_(rule.prefix, st)
            self.setLookAheadCoverage_(rule.suffix, st)
            self.setInputCoverage_(rule.glyphs, st)
        else:
            self.setCoverage_(rule.glyphs, st)
        self.buildLookupList(rule, st)
        return st

    def buildLookupList(self, rule, st):
        for sequenceIndex, lookupList in enumerate(rule.lookups):
            if lookupList is not None:
                if not isinstance(lookupList, list):
                    # Can happen with synthesised lookups
                    lookupList = [lookupList]
                for l in lookupList:
                    if l.lookup_index is None:
                        if isinstance(self, ChainContextPosBuilder):
                            other = "substitution"
                        else:
                            other = "positioning"
                        raise OpenTypeLibError(
                            "Missing index of the specified "
                            f"lookup, might be a {other} lookup",
                            self.location,
                        )
                    rec = self.newLookupRecord_(st)
                    rec.SequenceIndex = sequenceIndex
                    rec.LookupListIndex = l.lookup_index

    def add_subtable_break(self, location):
        self.rules.append(
            ChainContextualRule(
                self.SUBTABLE_BREAK_,
                self.SUBTABLE_BREAK_,
                self.SUBTABLE_BREAK_,
                [self.SUBTABLE_BREAK_],
            )
        )

    def newSubtable_(self, chaining=True):
        subtablename = f"Context{self.subtable_type}"
        if chaining:
            subtablename = "Chain" + subtablename
        st = getattr(ot, subtablename)()  # ot.ChainContextPos()/ot.ChainSubst()/etc.
        setattr(st, f"{self.subtable_type}Count", 0)
        setattr(st, f"{self.subtable_type}LookupRecord", [])
        return st

    # Format 1 and format 2 GSUB5/GSUB6/GPOS7/GPOS8 rulesets and rules form a family:
    #
    #       format 1 ruleset      format 1 rule      format 2 ruleset      format 2 rule
    # GSUB5 SubRuleSet            SubRule            SubClassSet           SubClassRule
    # GSUB6 ChainSubRuleSet       ChainSubRule       ChainSubClassSet      ChainSubClassRule
    # GPOS7 PosRuleSet            PosRule            PosClassSet           PosClassRule
    # GPOS8 ChainPosRuleSet       ChainPosRule       ChainPosClassSet      ChainPosClassRule
    #
    # The following functions generate the attribute names and subtables according
    # to this naming convention.
    def ruleSetAttr_(self, format=1, chaining=True):
        if format == 1:
            formatType = "Rule"
        elif format == 2:
            formatType = "Class"
        else:
            raise AssertionError(formatType)
        subtablename = f"{self.subtable_type[0:3]}{formatType}Set"  # Sub, not Subst.
        if chaining:
            subtablename = "Chain" + subtablename
        return subtablename

    def ruleAttr_(self, format=1, chaining=True):
        if format == 1:
            formatType = ""
        elif format == 2:
            formatType = "Class"
        else:
            raise AssertionError(formatType)
        subtablename = f"{self.subtable_type[0:3]}{formatType}Rule"  # Sub, not Subst.
        if chaining:
            subtablename = "Chain" + subtablename
        return subtablename

    def newRuleSet_(self, format=1, chaining=True):
        st = getattr(
            ot, self.ruleSetAttr_(format, chaining)
        )()  # ot.ChainPosRuleSet()/ot.SubRuleSet()/etc.
        st.populateDefaults()
        return st

    def newRule_(self, format=1, chaining=True):
        st = getattr(
            ot, self.ruleAttr_(format, chaining)
        )()  # ot.ChainPosClassRule()/ot.SubClassRule()/etc.
        st.populateDefaults()
        return st

    def attachSubtableWithCount_(
        self, st, subtable_name, count_name, existing=None, index=None, chaining=False
    ):
        if chaining:
            subtable_name = "Chain" + subtable_name
            count_name = "Chain" + count_name

        if not hasattr(st, count_name):
            setattr(st, count_name, 0)
            setattr(st, subtable_name, [])

        if existing:
            new_subtable = existing
        else:
            # Create a new, empty subtable from otTables
            new_subtable = getattr(ot, subtable_name)()

        setattr(st, count_name, getattr(st, count_name) + 1)

        if index:
            getattr(st, subtable_name).insert(index, new_subtable)
        else:
            getattr(st, subtable_name).append(new_subtable)

        return new_subtable

    def newLookupRecord_(self, st):
        return self.attachSubtableWithCount_(
            st,
            f"{self.subtable_type}LookupRecord",
            f"{self.subtable_type}Count",
            chaining=False,
        )  # Oddly, it isn't ChainSubstLookupRecord


class ChainContextPosBuilder(ChainContextualBuilder):
    """Builds a Chained Contextual Positioning (GPOS8) lookup.

    Users are expected to manually add rules to the ``rules`` attribute after
    the object has been initialized, e.g.::

        # pos [A B] [C D] x' lookup lu1 y' z' lookup lu2 E;

        prefix  = [ ["A", "B"], ["C", "D"] ]
        suffix  = [ ["E"] ]
        glyphs  = [ ["x"], ["y"], ["z"] ]
        lookups = [ [lu1], None,  [lu2] ]
        builder.rules.append( (prefix, glyphs, suffix, lookups) )

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        rules: A list of tuples representing the rules in this lookup.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GPOS", 8)
        self.rules = []
        self.subtable_type = "Pos"

    def find_chainable_single_pos(self, lookups, glyphs, value):
        """Helper for add_single_pos_chained_()"""
        res = None
        for lookup in lookups[::-1]:
            if lookup == self.SUBTABLE_BREAK_:
                return res
            if isinstance(lookup, SinglePosBuilder) and all(
                lookup.can_add(glyph, value) for glyph in glyphs
            ):
                res = lookup
        return res


class ChainContextSubstBuilder(ChainContextualBuilder):
    """Builds a Chained Contextual Substitution (GSUB6) lookup.

    Users are expected to manually add rules to the ``rules`` attribute after
    the object has been initialized, e.g.::

        # sub [A B] [C D] x' lookup lu1 y' z' lookup lu2 E;

        prefix  = [ ["A", "B"], ["C", "D"] ]
        suffix  = [ ["E"] ]
        glyphs  = [ ["x"], ["y"], ["z"] ]
        lookups = [ [lu1], None,  [lu2] ]
        builder.rules.append( (prefix, glyphs, suffix, lookups) )

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        rules: A list of tuples representing the rules in this lookup.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GSUB", 6)
        self.rules = []  # (prefix, input, suffix, lookups)
        self.subtable_type = "Subst"

    def getAlternateGlyphs(self):
        result = {}
        for rule in self.rules:
            if rule.is_subtable_break:
                continue
            for lookups in rule.lookups:
                if not isinstance(lookups, list):
                    lookups = [lookups]
                for lookup in lookups:
                    if lookup is not None:
                        alts = lookup.getAlternateGlyphs()
                        for glyph, replacements in alts.items():
                            alts_for_glyph = result.setdefault(glyph, [])
                            alts_for_glyph.extend(
                                g for g in replacements if g not in alts_for_glyph
                            )
        return result

    def find_chainable_subst(self, mapping, builder_class):
        """Helper for add_{single,multi}_subst_chained_()"""
        res = None
        for rule in self.rules[::-1]:
            if rule.is_subtable_break:
                return res
            for sub in rule.lookups:
                if isinstance(sub, builder_class) and not any(
                    g in mapping and mapping[g] != sub.mapping[g] for g in sub.mapping
                ):
                    res = sub
        return res

    def find_chainable_ligature_subst(self, glyphs, replacement):
        """Helper for add_ligature_subst_chained_()"""
        res = None
        for rule in self.rules[::-1]:
            if rule.is_subtable_break:
                return res
            for sub in rule.lookups:
                if not isinstance(sub, LigatureSubstBuilder):
                    continue
                if all(
                    sub.ligatures.get(seq, replacement) == replacement
                    for seq in itertools.product(*glyphs)
                ):
                    res = sub
        return res


class LigatureSubstBuilder(LookupBuilder):
    """Builds a Ligature Substitution (GSUB4) lookup.

    Users are expected to manually add ligatures to the ``ligatures``
    attribute after the object has been initialized, e.g.::

        # sub f i by f_i;
        builder.ligatures[("f","f","i")] = "f_f_i"

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        ligatures: An ordered dictionary mapping a tuple of glyph names to the
            ligature glyphname.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GSUB", 4)
        self.ligatures = OrderedDict()  # {('f','f','i'): 'f_f_i'}

    def equals(self, other):
        return LookupBuilder.equals(self, other) and self.ligatures == other.ligatures

    def build(self):
        """Build the lookup.

        Returns:
            An ``otTables.Lookup`` object representing the ligature
            substitution lookup.
        """
        subtables = self.build_subst_subtables(
            self.ligatures, buildLigatureSubstSubtable
        )
        return self.buildLookup_(subtables)

    def getAlternateGlyphs(self):
        # https://github.com/fonttools/fonttools/issues/3845
        return {
            components[0]: [ligature]
            for components, ligature in self.ligatures.items()
            if len(components) == 1
        }

    def add_subtable_break(self, location):
        self.ligatures[(self.SUBTABLE_BREAK_, location)] = self.SUBTABLE_BREAK_


class MultipleSubstBuilder(LookupBuilder):
    """Builds a Multiple Substitution (GSUB2) lookup.

    Users are expected to manually add substitutions to the ``mapping``
    attribute after the object has been initialized, e.g.::

        # sub uni06C0 by uni06D5.fina hamza.above;
        builder.mapping["uni06C0"] = [ "uni06D5.fina", "hamza.above"]

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        mapping: An ordered dictionary mapping a glyph name to a list of
            substituted glyph names.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GSUB", 2)
        self.mapping = OrderedDict()

    def equals(self, other):
        return LookupBuilder.equals(self, other) and self.mapping == other.mapping

    def build(self):
        subtables = self.build_subst_subtables(self.mapping, buildMultipleSubstSubtable)
        return self.buildLookup_(subtables)

    def getAlternateGlyphs(self):
        # https://github.com/fonttools/fonttools/issues/3845
        return {
            glyph: replacements
            for glyph, replacements in self.mapping.items()
            if len(replacements) == 1
        }

    def add_subtable_break(self, location):
        self.mapping[(self.SUBTABLE_BREAK_, location)] = self.SUBTABLE_BREAK_


class CursivePosBuilder(LookupBuilder):
    """Builds a Cursive Positioning (GPOS3) lookup.

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        attachments: An ordered dictionary mapping a glyph name to a two-element
            tuple of ``otTables.Anchor`` objects.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GPOS", 3)
        self.attachments = {}

    def equals(self, other):
        return (
            LookupBuilder.equals(self, other) and self.attachments == other.attachments
        )

    def add_attachment(self, location, glyphs, entryAnchor, exitAnchor):
        """Adds attachment information to the cursive positioning lookup.

        Args:
            location: A string or tuple representing the location in the
                original source which produced this lookup. (Unused.)
            glyphs: A list of glyph names sharing these entry and exit
                anchor locations.
            entryAnchor: A ``otTables.Anchor`` object representing the
                entry anchor, or ``None`` if no entry anchor is present.
            exitAnchor: A ``otTables.Anchor`` object representing the
                exit anchor, or ``None`` if no exit anchor is present.
        """
        for glyph in glyphs:
            self.attachments[glyph] = (entryAnchor, exitAnchor)

    def build(self):
        """Build the lookup.

        Returns:
            An ``otTables.Lookup`` object representing the cursive
            positioning lookup.
        """
        attachments = [{}]
        for key in self.attachments:
            if key[0] == self.SUBTABLE_BREAK_:
                attachments.append({})
            else:
                attachments[-1][key] = self.attachments[key]
        subtables = [buildCursivePosSubtable(s, self.glyphMap) for s in attachments]
        return self.buildLookup_(subtables)

    def add_subtable_break(self, location):
        self.attachments[(self.SUBTABLE_BREAK_, location)] = (
            self.SUBTABLE_BREAK_,
            self.SUBTABLE_BREAK_,
        )


class MarkBasePosBuilder(LookupBuilder):
    """Builds a Mark-To-Base Positioning (GPOS4) lookup.

    Users are expected to manually add marks and bases to the ``marks``
    and ``bases`` attributes after the object has been initialized, e.g.::

        builder.marks["acute"]   = (0, a1)
        builder.marks["grave"]   = (0, a1)
        builder.marks["cedilla"] = (1, a2)
        builder.bases["a"] = {0: a3, 1: a5}
        builder.bases["b"] = {0: a4, 1: a5}

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        marks: An dictionary mapping a glyph name to a two-element
            tuple containing a mark class ID and ``otTables.Anchor`` object.
        bases: An dictionary mapping a glyph name to a dictionary of
            mark class IDs and ``otTables.Anchor`` object.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GPOS", 4)
        self.marks = {}  # glyphName -> (markClassName, anchor)
        self.bases = {}  # glyphName -> {markClassName: anchor}
        self.subtables_ = []

    def get_subtables_(self):
        subtables_ = self.subtables_
        if self.bases or self.marks:
            subtables_.append((self.marks, self.bases))
        return subtables_

    def equals(self, other):
        return (
            LookupBuilder.equals(self, other)
            and self.get_subtables_() == other.get_subtables_()
        )

    def inferGlyphClasses(self):
        result = {}
        for marks, bases in self.get_subtables_():
            result.update({glyph: 1 for glyph in bases})
            result.update({glyph: 3 for glyph in marks})
        return result

    def build(self):
        """Build the lookup.

        Returns:
            An ``otTables.Lookup`` object representing the mark-to-base
            positioning lookup.
        """
        subtables = []
        for subtable in self.get_subtables_():
            markClasses = self.buildMarkClasses_(subtable[0])
            marks = {}
            for mark, (mc, anchor) in subtable[0].items():
                if mc not in markClasses:
                    raise ValueError(
                        "Mark class %s not found for mark glyph %s" % (mc, mark)
                    )
                marks[mark] = (markClasses[mc], anchor)
            bases = {}
            for glyph, anchors in subtable[1].items():
                bases[glyph] = {}
                for mc, anchor in anchors.items():
                    if mc not in markClasses:
                        raise ValueError(
                            "Mark class %s not found for base glyph %s" % (mc, glyph)
                        )
                    bases[glyph][markClasses[mc]] = anchor
            subtables.append(buildMarkBasePosSubtable(marks, bases, self.glyphMap))
        return self.buildLookup_(subtables)

    def add_subtable_break(self, location):
        self.subtables_.append((self.marks, self.bases))
        self.marks = {}
        self.bases = {}


class MarkLigPosBuilder(LookupBuilder):
    """Builds a Mark-To-Ligature Positioning (GPOS5) lookup.

    Users are expected to manually add marks and bases to the ``marks``
    and ``ligatures`` attributes after the object has been initialized, e.g.::

        builder.marks["acute"]   = (0, a1)
        builder.marks["grave"]   = (0, a1)
        builder.marks["cedilla"] = (1, a2)
        builder.ligatures["f_i"] = [
            { 0: a3, 1: a5 }, # f
            { 0: a4, 1: a5 }  # i
        ]

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        marks: An dictionary mapping a glyph name to a two-element
            tuple containing a mark class ID and ``otTables.Anchor`` object.
        ligatures: An dictionary mapping a glyph name to an array with one
            element for each ligature component. Each array element should be
            a dictionary mapping mark class IDs to ``otTables.Anchor`` objects.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GPOS", 5)
        self.marks = {}  # glyphName -> (markClassName, anchor)
        self.ligatures = {}  # glyphName -> [{markClassName: anchor}, ...]
        self.subtables_ = []

    def get_subtables_(self):
        subtables_ = self.subtables_
        if self.ligatures or self.marks:
            subtables_.append((self.marks, self.ligatures))
        return subtables_

    def equals(self, other):
        return (
            LookupBuilder.equals(self, other)
            and self.get_subtables_() == other.get_subtables_()
        )

    def inferGlyphClasses(self):
        result = {}
        for marks, ligatures in self.get_subtables_():
            result.update({glyph: 2 for glyph in ligatures})
            result.update({glyph: 3 for glyph in marks})
        return result

    def build(self):
        """Build the lookup.

        Returns:
            An ``otTables.Lookup`` object representing the mark-to-ligature
            positioning lookup.
        """
        subtables = []
        for subtable in self.get_subtables_():
            markClasses = self.buildMarkClasses_(subtable[0])
            marks = {
                mark: (markClasses[mc], anchor)
                for mark, (mc, anchor) in subtable[0].items()
            }
            ligs = {}
            for lig, components in subtable[1].items():
                ligs[lig] = []
                for c in components:
                    ligs[lig].append({markClasses[mc]: a for mc, a in c.items()})
            subtables.append(buildMarkLigPosSubtable(marks, ligs, self.glyphMap))
        return self.buildLookup_(subtables)

    def add_subtable_break(self, location):
        self.subtables_.append((self.marks, self.ligatures))
        self.marks = {}
        self.ligatures = {}


class MarkMarkPosBuilder(LookupBuilder):
    """Builds a Mark-To-Mark Positioning (GPOS6) lookup.

    Users are expected to manually add marks and bases to the ``marks``
    and ``baseMarks`` attributes after the object has been initialized, e.g.::

        builder.marks["acute"]     = (0, a1)
        builder.marks["grave"]     = (0, a1)
        builder.marks["cedilla"]   = (1, a2)
        builder.baseMarks["acute"] = {0: a3}

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        marks: An dictionary mapping a glyph name to a two-element
            tuple containing a mark class ID and ``otTables.Anchor`` object.
        baseMarks: An dictionary mapping a glyph name to a dictionary
            containing one item: a mark class ID and a ``otTables.Anchor`` object.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GPOS", 6)
        self.marks = {}  # glyphName -> (markClassName, anchor)
        self.baseMarks = {}  # glyphName -> {markClassName: anchor}
        self.subtables_ = []

    def get_subtables_(self):
        subtables_ = self.subtables_
        if self.baseMarks or self.marks:
            subtables_.append((self.marks, self.baseMarks))
        return subtables_

    def equals(self, other):
        return (
            LookupBuilder.equals(self, other)
            and self.get_subtables_() == other.get_subtables_()
        )

    def inferGlyphClasses(self):
        result = {}
        for marks, baseMarks in self.get_subtables_():
            result.update({glyph: 3 for glyph in baseMarks})
            result.update({glyph: 3 for glyph in marks})
        return result

    def build(self):
        """Build the lookup.

        Returns:
            An ``otTables.Lookup`` object representing the mark-to-mark
            positioning lookup.
        """
        subtables = []
        for subtable in self.get_subtables_():
            markClasses = self.buildMarkClasses_(subtable[0])
            markClassList = sorted(markClasses.keys(), key=markClasses.get)
            marks = {
                mark: (markClasses[mc], anchor)
                for mark, (mc, anchor) in subtable[0].items()
            }

            st = ot.MarkMarkPos()
            st.Format = 1
            st.ClassCount = len(markClasses)
            st.Mark1Coverage = buildCoverage(marks, self.glyphMap)
            st.Mark2Coverage = buildCoverage(subtable[1], self.glyphMap)
            st.Mark1Array = buildMarkArray(marks, self.glyphMap)
            st.Mark2Array = ot.Mark2Array()
            st.Mark2Array.Mark2Count = len(st.Mark2Coverage.glyphs)
            st.Mark2Array.Mark2Record = []
            for base in st.Mark2Coverage.glyphs:
                anchors = [subtable[1][base].get(mc) for mc in markClassList]
                st.Mark2Array.Mark2Record.append(buildMark2Record(anchors))
            subtables.append(st)
        return self.buildLookup_(subtables)

    def add_subtable_break(self, location):
        self.subtables_.append((self.marks, self.baseMarks))
        self.marks = {}
        self.baseMarks = {}


class ReverseChainSingleSubstBuilder(LookupBuilder):
    """Builds a Reverse Chaining Contextual Single Substitution (GSUB8) lookup.

    Users are expected to manually add substitutions to the ``substitutions``
    attribute after the object has been initialized, e.g.::

        # reversesub [a e n] d' by d.alt;
        prefix = [ ["a", "e", "n"] ]
        suffix = []
        mapping = { "d": "d.alt" }
        builder.substitutions.append( (prefix, suffix, mapping) )

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        substitutions: A three-element tuple consisting of a prefix sequence,
            a suffix sequence, and a dictionary of single substitutions.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GSUB", 8)
        self.rules = []  # (prefix, suffix, mapping)

    def equals(self, other):
        return LookupBuilder.equals(self, other) and self.rules == other.rules

    def build(self):
        """Build the lookup.

        Returns:
            An ``otTables.Lookup`` object representing the chained
            contextual substitution lookup.
        """
        subtables = []
        for prefix, suffix, mapping in self.rules:
            st = ot.ReverseChainSingleSubst()
            st.Format = 1
            self.setBacktrackCoverage_(prefix, st)
            self.setLookAheadCoverage_(suffix, st)
            st.Coverage = buildCoverage(mapping.keys(), self.glyphMap)
            st.GlyphCount = len(mapping)
            st.Substitute = [mapping[g] for g in st.Coverage.glyphs]
            subtables.append(st)
        return self.buildLookup_(subtables)

    def add_subtable_break(self, location):
        # Nothing to do here, each substitution is in its own subtable.
        pass


class AnySubstBuilder(LookupBuilder):
    """A temporary builder for Single, Multiple, or Ligature substitution lookup.

    Users are expected to manually add substitutions to the ``mapping``
    attribute after the object has been initialized, e.g.::

        # sub x by y;
        builder.mapping[("x",)] = ("y",)
        # sub a by b c;
        builder.mapping[("a",)] = ("b", "c")
        # sub f i by f_i;
        builder.mapping[("f", "i")] = ("f_i",)

    Then call `promote_lookup_type()` to convert this builder into the
    appropriate type of substitution lookup builder. This would promote single
    substitutions to either multiple or ligature substitutions, depending on the
    rest of the rules in the mapping.

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        mapping: An ordered dictionary mapping a tuple of glyph names to another
            tuple of glyph names.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GSUB", 0)
        self.mapping = OrderedDict()

    def _add_to_single_subst(self, builder, key, value):
        if key[0] != self.SUBTABLE_BREAK_:
            key = key[0]
        builder.mapping[key] = value[0]

    def _add_to_multiple_subst(self, builder, key, value):
        if key[0] != self.SUBTABLE_BREAK_:
            key = key[0]
        builder.mapping[key] = value

    def _add_to_ligature_subst(self, builder, key, value):
        builder.ligatures[key] = value[0]

    def promote_lookup_type(self, is_named_lookup):
        # https://github.com/fonttools/fonttools/issues/612
        # A multiple substitution may have a single destination, in which case
        # it will look just like a single substitution. So if there are both
        # multiple and single substitutions, upgrade all the single ones to
        # multiple substitutions. Similarly, a ligature substitution may have a
        # single source glyph, so if there are both ligature and single
        # substitutions, upgrade all the single ones to ligature substitutions.
        builder_classes = []
        for key, value in self.mapping.items():
            if key[0] == self.SUBTABLE_BREAK_:
                builder_classes.append(None)
            elif len(key) == 1 and len(value) == 1:
                builder_classes.append(SingleSubstBuilder)
            elif len(key) == 1 and len(value) != 1:
                builder_classes.append(MultipleSubstBuilder)
            elif len(key) > 1 and len(value) == 1:
                builder_classes.append(LigatureSubstBuilder)
            else:
                assert False, "Should not happen"

        has_multiple = any(b is MultipleSubstBuilder for b in builder_classes)
        has_ligature = any(b is LigatureSubstBuilder for b in builder_classes)

        # If we have mixed single and multiple substitutions,
        # upgrade all single substitutions to multiple substitutions.
        to_multiple = has_multiple and not has_ligature

        # If we have mixed single and ligature substitutions,
        # upgrade all single substitutions to ligature substitutions.
        to_ligature = has_ligature and not has_multiple

        # If we have only single substitutions, we can keep them as is.
        to_single = not has_ligature and not has_multiple

        ret = []
        if to_single:
            builder = SingleSubstBuilder(self.font, self.location)
            for key, value in self.mapping.items():
                self._add_to_single_subst(builder, key, value)
            ret = [builder]
        elif to_multiple:
            builder = MultipleSubstBuilder(self.font, self.location)
            for key, value in self.mapping.items():
                self._add_to_multiple_subst(builder, key, value)
            ret = [builder]
        elif to_ligature:
            builder = LigatureSubstBuilder(self.font, self.location)
            for key, value in self.mapping.items():
                self._add_to_ligature_subst(builder, key, value)
            ret = [builder]
        elif is_named_lookup:
            # This is a named lookup with mixed substitutions that can’t be promoted,
            # since we can’t split it into multiple lookups, we return None here to
            # signal that to the caller
            return None
        else:
            curr_builder = None
            for builder_class, (key, value) in zip(
                builder_classes, self.mapping.items()
            ):
                if curr_builder is None or type(curr_builder) is not builder_class:
                    curr_builder = builder_class(self.font, self.location)
                    ret.append(curr_builder)
                if builder_class is SingleSubstBuilder:
                    self._add_to_single_subst(curr_builder, key, value)
                elif builder_class is MultipleSubstBuilder:
                    self._add_to_multiple_subst(curr_builder, key, value)
                elif builder_class is LigatureSubstBuilder:
                    self._add_to_ligature_subst(curr_builder, key, value)
                else:
                    assert False, "Should not happen"

        for builder in ret:
            builder.extension = self.extension
            builder.lookupflag = self.lookupflag
            builder.markFilterSet = self.markFilterSet
        return ret

    def equals(self, other):
        return LookupBuilder.equals(self, other) and self.mapping == other.mapping

    def build(self):
        assert False

    def getAlternateGlyphs(self):
        return {
            key[0]: value
            for key, value in self.mapping.items()
            if len(key) == 1 and len(value) == 1
        }

    def add_subtable_break(self, location):
        self.mapping[(self.SUBTABLE_BREAK_, location)] = self.SUBTABLE_BREAK_


class SingleSubstBuilder(LookupBuilder):
    """Builds a Single Substitution (GSUB1) lookup.

    Users are expected to manually add substitutions to the ``mapping``
    attribute after the object has been initialized, e.g.::

        # sub x by y;
        builder.mapping["x"] = "y"

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        mapping: A dictionary mapping a single glyph name to another glyph name.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GSUB", 1)
        self.mapping = OrderedDict()

    def equals(self, other):
        return LookupBuilder.equals(self, other) and self.mapping == other.mapping

    def build(self):
        """Build the lookup.

        Returns:
            An ``otTables.Lookup`` object representing the multiple
            substitution lookup.
        """
        subtables = self.build_subst_subtables(self.mapping, buildSingleSubstSubtable)
        return self.buildLookup_(subtables)

    def getAlternateGlyphs(self):
        return {glyph: [repl] for glyph, repl in self.mapping.items()}

    def add_subtable_break(self, location):
        self.mapping[(self.SUBTABLE_BREAK_, location)] = self.SUBTABLE_BREAK_


class ClassPairPosSubtableBuilder(object):
    """Builds class-based Pair Positioning (GPOS2 format 2) subtables.

    Note that this does *not* build a GPOS2 ``otTables.Lookup`` directly,
    but builds a list of ``otTables.PairPos`` subtables. It is used by the
    :class:`PairPosBuilder` below.

    Attributes:
        builder (PairPosBuilder): A pair positioning lookup builder.
    """

    def __init__(self, builder):
        self.builder_ = builder
        self.classDef1_, self.classDef2_ = None, None
        self.values_ = {}  # (glyphclass1, glyphclass2) --> (value1, value2)
        self.forceSubtableBreak_ = False
        self.subtables_ = []

    def addPair(self, gc1, value1, gc2, value2):
        """Add a pair positioning rule.

        Args:
            gc1: A set of glyph names for the "left" glyph
            value1: An ``otTables.ValueRecord`` object for the left glyph's
                positioning.
            gc2: A set of glyph names for the "right" glyph
            value2: An ``otTables.ValueRecord`` object for the right glyph's
                positioning.
        """
        mergeable = (
            not self.forceSubtableBreak_
            and self.classDef1_ is not None
            and self.classDef1_.canAdd(gc1)
            and self.classDef2_ is not None
            and self.classDef2_.canAdd(gc2)
        )
        if not mergeable:
            self.flush_()
            self.classDef1_ = ClassDefBuilder(useClass0=True)
            self.classDef2_ = ClassDefBuilder(useClass0=False)
            self.values_ = {}
        self.classDef1_.add(gc1)
        self.classDef2_.add(gc2)
        self.values_[(gc1, gc2)] = (value1, value2)

    def addSubtableBreak(self):
        """Add an explicit subtable break at this point."""
        self.forceSubtableBreak_ = True

    def subtables(self):
        """Return the list of ``otTables.PairPos`` subtables constructed."""
        self.flush_()
        return self.subtables_

    def flush_(self):
        if self.classDef1_ is None or self.classDef2_ is None:
            return
        st = buildPairPosClassesSubtable(self.values_, self.builder_.glyphMap)
        if st.Coverage is None:
            return
        self.subtables_.append(st)
        self.forceSubtableBreak_ = False


class PairPosBuilder(LookupBuilder):
    """Builds a Pair Positioning (GPOS2) lookup.

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        pairs: An array of class-based pair positioning tuples. Usually
            manipulated with the :meth:`addClassPair` method below.
        glyphPairs: A dictionary mapping a tuple of glyph names to a tuple
            of ``otTables.ValueRecord`` objects. Usually manipulated with the
            :meth:`addGlyphPair` method below.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GPOS", 2)
        self.pairs = []  # [(gc1, value1, gc2, value2)*]
        self.glyphPairs = {}  # (glyph1, glyph2) --> (value1, value2)
        self.locations = {}  # (gc1, gc2) --> (filepath, line, column)

    def addClassPair(self, location, glyphclass1, value1, glyphclass2, value2):
        """Add a class pair positioning rule to the current lookup.

        Args:
            location: A string or tuple representing the location in the
                original source which produced this rule. Unused.
            glyphclass1: A set of glyph names for the "left" glyph in the pair.
            value1: A ``otTables.ValueRecord`` for positioning the left glyph.
            glyphclass2: A set of glyph names for the "right" glyph in the pair.
            value2: A ``otTables.ValueRecord`` for positioning the right glyph.
        """
        self.pairs.append((glyphclass1, value1, glyphclass2, value2))

    def addGlyphPair(self, location, glyph1, value1, glyph2, value2):
        """Add a glyph pair positioning rule to the current lookup.

        Args:
            location: A string or tuple representing the location in the
                original source which produced this rule.
            glyph1: A glyph name for the "left" glyph in the pair.
            value1: A ``otTables.ValueRecord`` for positioning the left glyph.
            glyph2: A glyph name for the "right" glyph in the pair.
            value2: A ``otTables.ValueRecord`` for positioning the right glyph.
        """
        key = (glyph1, glyph2)
        oldValue = self.glyphPairs.get(key, None)
        if oldValue is not None:
            # the Feature File spec explicitly allows specific pairs generated
            # by an 'enum' rule to be overridden by preceding single pairs
            otherLoc = self.locations[key]
            log.debug(
                "Already defined position for pair %s %s at %s; "
                "choosing the first value",
                glyph1,
                glyph2,
                otherLoc,
            )
        else:
            self.glyphPairs[key] = (value1, value2)
            self.locations[key] = location

    def add_subtable_break(self, location):
        self.pairs.append(
            (
                self.SUBTABLE_BREAK_,
                self.SUBTABLE_BREAK_,
                self.SUBTABLE_BREAK_,
                self.SUBTABLE_BREAK_,
            )
        )

    def equals(self, other):
        return (
            LookupBuilder.equals(self, other)
            and self.glyphPairs == other.glyphPairs
            and self.pairs == other.pairs
        )

    def build(self):
        """Build the lookup.

        Returns:
            An ``otTables.Lookup`` object representing the pair positioning
            lookup.
        """
        builders = {}
        builder = ClassPairPosSubtableBuilder(self)
        for glyphclass1, value1, glyphclass2, value2 in self.pairs:
            if glyphclass1 is self.SUBTABLE_BREAK_:
                builder.addSubtableBreak()
                continue
            builder.addPair(glyphclass1, value1, glyphclass2, value2)
        subtables = []
        if self.glyphPairs:
            subtables.extend(buildPairPosGlyphs(self.glyphPairs, self.glyphMap))
        subtables.extend(builder.subtables())
        lookup = self.buildLookup_(subtables)

        # Compact the lookup
        # This is a good moment to do it because the compaction should create
        # smaller subtables, which may prevent overflows from happening.
        # Keep reading the value from the ENV until ufo2ft switches to the config system
        level = self.font.cfg.get(
            "fontTools.otlLib.optimize.gpos:COMPRESSION_LEVEL",
            default=_compression_level_from_env(),
        )
        if level != 0:
            log.info("Compacting GPOS...")
            compact_lookup(self.font, level, lookup)

        return lookup


class SinglePosBuilder(LookupBuilder):
    """Builds a Single Positioning (GPOS1) lookup.

    Attributes:
        font (``fontTools.TTLib.TTFont``): A font object.
        location: A string or tuple representing the location in the original
            source which produced this lookup.
        mapping: A dictionary mapping a glyph name to a ``otTables.ValueRecord``
            objects. Usually manipulated with the :meth:`add_pos` method below.
        lookupflag (int): The lookup's flag
        markFilterSet: Either ``None`` if no mark filtering set is used, or
            an integer representing the filtering set to be used for this
            lookup. If a mark filtering set is provided,
            `LOOKUP_FLAG_USE_MARK_FILTERING_SET` will be set on the lookup's
            flags.
    """

    def __init__(self, font, location):
        LookupBuilder.__init__(self, font, location, "GPOS", 1)
        self.locations = {}  # glyph -> (filename, line, column)
        self.mapping = {}  # glyph -> ot.ValueRecord

    def add_pos(self, location, glyph, otValueRecord):
        """Add a single positioning rule.

        Args:
            location: A string or tuple representing the location in the
                original source which produced this lookup.
            glyph: A glyph name.
            otValueRection: A ``otTables.ValueRecord`` used to position the
                glyph.
        """
        if otValueRecord is None:
            otValueRecord = ValueRecord()
        if not self.can_add(glyph, otValueRecord):
            otherLoc = self.locations[glyph]
            raise OpenTypeLibError(
                'Already defined different position for glyph "%s" at %s'
                % (glyph, otherLoc),
                location,
            )
        if otValueRecord:
            self.mapping[glyph] = otValueRecord
        self.locations[glyph] = location

    def can_add(self, glyph, value):
        assert isinstance(value, ValueRecord)
        curValue = self.mapping.get(glyph)
        return curValue is None or curValue == value

    def equals(self, other):
        return LookupBuilder.equals(self, other) and self.mapping == other.mapping

    def build(self):
        """Build the lookup.

        Returns:
            An ``otTables.Lookup`` object representing the single positioning
            lookup.
        """
        subtables = buildSinglePos(self.mapping, self.glyphMap)
        return self.buildLookup_(subtables)


# GSUB


def buildSingleSubstSubtable(mapping):
    """Builds a single substitution (GSUB1) subtable.

    Note that if you are implementing a layout compiler, you may find it more
    flexible to use
    :py:class:`fontTools.otlLib.lookupBuilders.SingleSubstBuilder` instead.

    Args:
        mapping: A dictionary mapping input glyph names to output glyph names.

    Returns:
        An ``otTables.SingleSubst`` object, or ``None`` if the mapping dictionary
        is empty.
    """
    if not mapping:
        return None
    self = ot.SingleSubst()
    self.mapping = dict(mapping)
    return self


def buildMultipleSubstSubtable(mapping):
    """Builds a multiple substitution (GSUB2) subtable.

    Note that if you are implementing a layout compiler, you may find it more
    flexible to use
    :py:class:`fontTools.otlLib.lookupBuilders.MultipleSubstBuilder` instead.

    Example::

        # sub uni06C0 by uni06D5.fina hamza.above
        # sub uni06C2 by uni06C1.fina hamza.above;

        subtable = buildMultipleSubstSubtable({
            "uni06C0": [ "uni06D5.fina", "hamza.above"],
            "uni06C2": [ "uni06D1.fina", "hamza.above"]
        })

    Args:
        mapping: A dictionary mapping input glyph names to a list of output
            glyph names.

    Returns:
        An ``otTables.MultipleSubst`` object or ``None`` if the mapping dictionary
        is empty.
    """
    if not mapping:
        return None
    self = ot.MultipleSubst()
    self.mapping = dict(mapping)
    return self


def buildAlternateSubstSubtable(mapping):
    """Builds an alternate substitution (GSUB3) subtable.

    Note that if you are implementing a layout compiler, you may find it more
    flexible to use
    :py:class:`fontTools.otlLib.lookupBuilders.AlternateSubstBuilder` instead.

    Args:
        mapping: A dictionary mapping input glyph names to a list of output
            glyph names.

    Returns:
        An ``otTables.AlternateSubst`` object or ``None`` if the mapping dictionary
        is empty.
    """
    if not mapping:
        return None
    self = ot.AlternateSubst()
    self.alternates = dict(mapping)
    return self


def buildLigatureSubstSubtable(mapping):
    """Builds a ligature substitution (GSUB4) subtable.

    Note that if you are implementing a layout compiler, you may find it more
    flexible to use
    :py:class:`fontTools.otlLib.lookupBuilders.LigatureSubstBuilder` instead.

    Example::

        # sub f f i by f_f_i;
        # sub f i by f_i;

        subtable = buildLigatureSubstSubtable({
            ("f", "f", "i"): "f_f_i",
            ("f", "i"): "f_i",
        })

    Args:
        mapping: A dictionary mapping tuples of glyph names to output
            glyph names.

    Returns:
        An ``otTables.LigatureSubst`` object or ``None`` if the mapping dictionary
        is empty.
    """

    if not mapping:
        return None
    self = ot.LigatureSubst()
    # The following single line can replace the rest of this function
    # with fontTools >= 3.1:
    # self.ligatures = dict(mapping)
    self.ligatures = {}
    for components in sorted(mapping.keys(), key=self._getLigatureSortKey):
        ligature = ot.Ligature()
        ligature.Component = components[1:]
        ligature.CompCount = len(ligature.Component) + 1
        ligature.LigGlyph = mapping[components]
        firstGlyph = components[0]
        self.ligatures.setdefault(firstGlyph, []).append(ligature)
    return self


# GPOS


def buildAnchor(x, y, point=None, deviceX=None, deviceY=None):
    """Builds an Anchor table.

    This determines the appropriate anchor format based on the passed parameters.

    Args:
        x (int): X coordinate.
        y (int): Y coordinate.
        point (int): Index of glyph contour point, if provided.
        deviceX (``otTables.Device``): X coordinate device table, if provided.
        deviceY (``otTables.Device``): Y coordinate device table, if provided.

    Returns:
        An ``otTables.Anchor`` object.
    """
    self = ot.Anchor()
    self.XCoordinate, self.YCoordinate = x, y
    self.Format = 1
    if point is not None:
        self.AnchorPoint = point
        self.Format = 2
    if deviceX is not None or deviceY is not None:
        assert (
            self.Format == 1
        ), "Either point, or both of deviceX/deviceY, must be None."
        self.XDeviceTable = deviceX
        self.YDeviceTable = deviceY
        self.Format = 3
    return self


def buildBaseArray(bases, numMarkClasses, glyphMap):
    """Builds a base array record.

    As part of building mark-to-base positioning rules, you will need to define
    a ``BaseArray`` record, which "defines for each base glyph an array of
    anchors, one for each mark class." This function builds the base array
    subtable.

    Example::

        bases = {"a": {0: a3, 1: a5}, "b": {0: a4, 1: a5}}
        basearray = buildBaseArray(bases, 2, font.getReverseGlyphMap())

    Args:
        bases (dict): A dictionary mapping anchors to glyphs; the keys being
            glyph names, and the values being dictionaries mapping mark class ID
            to the appropriate ``otTables.Anchor`` object used for attaching marks
            of that class.
        numMarkClasses (int): The total number of mark classes for which anchors
            are defined.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns:
        An ``otTables.BaseArray`` object.
    """
    self = ot.BaseArray()
    self.BaseRecord = []
    for base in sorted(bases, key=glyphMap.__getitem__):
        b = bases[base]
        anchors = [b.get(markClass) for markClass in range(numMarkClasses)]
        self.BaseRecord.append(buildBaseRecord(anchors))
    self.BaseCount = len(self.BaseRecord)
    return self


def buildBaseRecord(anchors):
    # [otTables.Anchor, otTables.Anchor, ...] --> otTables.BaseRecord
    self = ot.BaseRecord()
    self.BaseAnchor = anchors
    return self


def buildComponentRecord(anchors):
    """Builds a component record.

    As part of building mark-to-ligature positioning rules, you will need to
    define ``ComponentRecord`` objects, which contain "an array of offsets...
    to the Anchor tables that define all the attachment points used to attach
    marks to the component." This function builds the component record.

    Args:
        anchors: A list of ``otTables.Anchor`` objects or ``None``.

    Returns:
        A ``otTables.ComponentRecord`` object or ``None`` if no anchors are
        supplied.
    """
    if not anchors:
        return None
    self = ot.ComponentRecord()
    self.LigatureAnchor = anchors
    return self


def buildCursivePosSubtable(attach, glyphMap):
    """Builds a cursive positioning (GPOS3) subtable.

    Cursive positioning lookups are made up of a coverage table of glyphs,
    and a set of ``EntryExitRecord`` records containing the anchors for
    each glyph. This function builds the cursive positioning subtable.

    Example::

        subtable = buildCursivePosSubtable({
            "AlifIni": (None, buildAnchor(0, 50)),
            "BehMed": (buildAnchor(500,250), buildAnchor(0,50)),
            # ...
        }, font.getReverseGlyphMap())

    Args:
        attach (dict): A mapping between glyph names and a tuple of two
            ``otTables.Anchor`` objects representing entry and exit anchors.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns:
        An ``otTables.CursivePos`` object, or ``None`` if the attachment
        dictionary was empty.
    """
    if not attach:
        return None
    self = ot.CursivePos()
    self.Format = 1
    self.Coverage = buildCoverage(attach.keys(), glyphMap)
    self.EntryExitRecord = []
    for glyph in self.Coverage.glyphs:
        entryAnchor, exitAnchor = attach[glyph]
        rec = ot.EntryExitRecord()
        rec.EntryAnchor = entryAnchor
        rec.ExitAnchor = exitAnchor
        self.EntryExitRecord.append(rec)
    self.EntryExitCount = len(self.EntryExitRecord)
    return self


def buildDevice(deltas):
    """Builds a Device record as part of a ValueRecord or Anchor.

    Device tables specify size-specific adjustments to value records
    and anchors to reflect changes based on the resolution of the output.
    For example, one could specify that an anchor's Y position should be
    increased by 1 pixel when displayed at 8 pixels per em. This routine
    builds device records.

    Args:
        deltas: A dictionary mapping pixels-per-em sizes to the delta
            adjustment in pixels when the font is displayed at that size.

    Returns:
        An ``otTables.Device`` object if any deltas were supplied, or
        ``None`` otherwise.
    """
    if not deltas:
        return None
    self = ot.Device()
    keys = deltas.keys()
    self.StartSize = startSize = min(keys)
    self.EndSize = endSize = max(keys)
    assert 0 <= startSize <= endSize
    self.DeltaValue = deltaValues = [
        deltas.get(size, 0) for size in range(startSize, endSize + 1)
    ]
    maxDelta = max(deltaValues)
    minDelta = min(deltaValues)
    assert minDelta > -129 and maxDelta < 128
    if minDelta > -3 and maxDelta < 2:
        self.DeltaFormat = 1
    elif minDelta > -9 and maxDelta < 8:
        self.DeltaFormat = 2
    else:
        self.DeltaFormat = 3
    return self


def buildLigatureArray(ligs, numMarkClasses, glyphMap):
    """Builds a LigatureArray subtable.

    As part of building a mark-to-ligature lookup, you will need to define
    the set of anchors (for each mark class) on each component of the ligature
    where marks can be attached. For example, for an Arabic divine name ligature
    (lam lam heh), you may want to specify mark attachment positioning for
    superior marks (fatha, etc.) and inferior marks (kasra, etc.) on each glyph
    of the ligature. This routine builds the ligature array record.

    Example::

        buildLigatureArray({
            "lam-lam-heh": [
                { 0: superiorAnchor1, 1: inferiorAnchor1 }, # attach points for lam1
                { 0: superiorAnchor2, 1: inferiorAnchor2 }, # attach points for lam2
                { 0: superiorAnchor3, 1: inferiorAnchor3 }, # attach points for heh
            ]
        }, 2, font.getReverseGlyphMap())

    Args:
        ligs (dict): A mapping of ligature names to an array of dictionaries:
            for each component glyph in the ligature, an dictionary mapping
            mark class IDs to anchors.
        numMarkClasses (int): The number of mark classes.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns:
        An ``otTables.LigatureArray`` object if deltas were supplied.
    """
    self = ot.LigatureArray()
    self.LigatureAttach = []
    for lig in sorted(ligs, key=glyphMap.__getitem__):
        anchors = []
        for component in ligs[lig]:
            anchors.append([component.get(mc) for mc in range(numMarkClasses)])
        self.LigatureAttach.append(buildLigatureAttach(anchors))
    self.LigatureCount = len(self.LigatureAttach)
    return self


def buildLigatureAttach(components):
    # [[Anchor, Anchor], [Anchor, Anchor, Anchor]] --> LigatureAttach
    self = ot.LigatureAttach()
    self.ComponentRecord = [buildComponentRecord(c) for c in components]
    self.ComponentCount = len(self.ComponentRecord)
    return self


def buildMarkArray(marks, glyphMap):
    """Builds a mark array subtable.

    As part of building mark-to-* positioning rules, you will need to define
    a MarkArray subtable, which "defines the class and the anchor point
    for a mark glyph." This function builds the mark array subtable.

    Example::

        mark = {
            "acute": (0, buildAnchor(300,712)),
            # ...
        }
        markarray = buildMarkArray(marks, font.getReverseGlyphMap())

    Args:
        marks (dict): A dictionary mapping anchors to glyphs; the keys being
            glyph names, and the values being a tuple of mark class number and
            an ``otTables.Anchor`` object representing the mark's attachment
            point.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns:
        An ``otTables.MarkArray`` object.
    """
    self = ot.MarkArray()
    self.MarkRecord = []
    for mark in sorted(marks.keys(), key=glyphMap.__getitem__):
        markClass, anchor = marks[mark]
        markrec = buildMarkRecord(markClass, anchor)
        self.MarkRecord.append(markrec)
    self.MarkCount = len(self.MarkRecord)
    return self


@deprecateFunction(
    "use buildMarkBasePosSubtable() instead", category=DeprecationWarning
)
def buildMarkBasePos(marks, bases, glyphMap):
    """Build a list of MarkBasePos (GPOS4) subtables.

    .. deprecated:: 4.58.0
           Use :func:`buildMarkBasePosSubtable` instead.
    """
    return [buildMarkBasePosSubtable(marks, bases, glyphMap)]


def buildMarkBasePosSubtable(marks, bases, glyphMap):
    """Build a single MarkBasePos (GPOS4) subtable.

    This builds a mark-to-base lookup subtable containing all of the referenced
    marks and bases.

    Example::

        # a1, a2, a3, a4, a5 = buildAnchor(500, 100), ...

        marks = {"acute": (0, a1), "grave": (0, a1), "cedilla": (1, a2)}
        bases = {"a": {0: a3, 1: a5}, "b": {0: a4, 1: a5}}
        markbaseposes = [buildMarkBasePosSubtable(marks, bases, font.getReverseGlyphMap())]

    Args:
        marks (dict): A dictionary mapping anchors to glyphs; the keys being
            glyph names, and the values being a tuple of mark class number and
            an ``otTables.Anchor`` object representing the mark's attachment
            point. (See :func:`buildMarkArray`.)
        bases (dict): A dictionary mapping anchors to glyphs; the keys being
            glyph names, and the values being dictionaries mapping mark class ID
            to the appropriate ``otTables.Anchor`` object used for attaching marks
            of that class. (See :func:`buildBaseArray`.)
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns:
        A ``otTables.MarkBasePos`` object.
    """
    self = ot.MarkBasePos()
    self.Format = 1
    self.MarkCoverage = buildCoverage(marks, glyphMap)
    self.MarkArray = buildMarkArray(marks, glyphMap)
    self.ClassCount = max([mc for mc, _ in marks.values()]) + 1
    self.BaseCoverage = buildCoverage(bases, glyphMap)
    self.BaseArray = buildBaseArray(bases, self.ClassCount, glyphMap)
    return self


@deprecateFunction("use buildMarkLigPosSubtable() instead", category=DeprecationWarning)
def buildMarkLigPos(marks, ligs, glyphMap):
    """Build a list of MarkLigPos (GPOS5) subtables.

    .. deprecated:: 4.58.0
       Use :func:`buildMarkLigPosSubtable` instead.
    """
    return [buildMarkLigPosSubtable(marks, ligs, glyphMap)]


def buildMarkLigPosSubtable(marks, ligs, glyphMap):
    """Build a single MarkLigPos (GPOS5) subtable.

    This builds a mark-to-base lookup subtable containing all of the referenced
    marks and bases.

    Note that if you are implementing a layout compiler, you may find it more
    flexible to use
    :py:class:`fontTools.otlLib.lookupBuilders.MarkLigPosBuilder` instead.

    Example::

        # a1, a2, a3, a4, a5 = buildAnchor(500, 100), ...
        marks = {
            "acute": (0, a1),
            "grave": (0, a1),
            "cedilla": (1, a2)
        }
        ligs = {
            "f_i": [
                { 0: a3, 1: a5 }, # f
                { 0: a4, 1: a5 }  # i
                ],
        #   "c_t": [{...}, {...}]
        }
        markligpose = buildMarkLigPosSubtable(marks, ligs,
            font.getReverseGlyphMap())

    Args:
        marks (dict): A dictionary mapping anchors to glyphs; the keys being
            glyph names, and the values being a tuple of mark class number and
            an ``otTables.Anchor`` object representing the mark's attachment
            point. (See :func:`buildMarkArray`.)
        ligs (dict): A mapping of ligature names to an array of dictionaries:
            for each component glyph in the ligature, an dictionary mapping
            mark class IDs to anchors. (See :func:`buildLigatureArray`.)
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns:
        A ``otTables.MarkLigPos`` object.
    """
    self = ot.MarkLigPos()
    self.Format = 1
    self.MarkCoverage = buildCoverage(marks, glyphMap)
    self.MarkArray = buildMarkArray(marks, glyphMap)
    self.ClassCount = max([mc for mc, _ in marks.values()]) + 1
    self.LigatureCoverage = buildCoverage(ligs, glyphMap)
    self.LigatureArray = buildLigatureArray(ligs, self.ClassCount, glyphMap)
    return self


def buildMarkRecord(classID, anchor):
    assert isinstance(classID, int)
    assert isinstance(anchor, ot.Anchor)
    self = ot.MarkRecord()
    self.Class = classID
    self.MarkAnchor = anchor
    return self


def buildMark2Record(anchors):
    # [otTables.Anchor, otTables.Anchor, ...] --> otTables.Mark2Record
    self = ot.Mark2Record()
    self.Mark2Anchor = anchors
    return self


def _getValueFormat(f, values, i):
    # Helper for buildPairPos{Glyphs|Classes}Subtable.
    if f is not None:
        return f
    mask = 0
    for value in values:
        if value is not None and value[i] is not None:
            mask |= value[i].getFormat()
    return mask


def buildPairPosClassesSubtable(pairs, glyphMap, valueFormat1=None, valueFormat2=None):
    """Builds a class pair adjustment (GPOS2 format 2) subtable.

    Kerning tables are generally expressed as pair positioning tables using
    class-based pair adjustments. This routine builds format 2 PairPos
    subtables.

    Note that if you are implementing a layout compiler, you may find it more
    flexible to use
    :py:class:`fontTools.otlLib.lookupBuilders.ClassPairPosSubtableBuilder`
    instead, as this takes care of ensuring that the supplied pairs can be
    formed into non-overlapping classes and emitting individual subtables
    whenever the non-overlapping requirement means that a new subtable is
    required.

    Example::

        pairs = {}

        pairs[(
            [ "K", "X" ],
            [ "W", "V" ]
        )] = ( buildValue(xAdvance=+5), buildValue() )
        # pairs[(... , ...)] = (..., ...)

        pairpos = buildPairPosClassesSubtable(pairs, font.getReverseGlyphMap())

    Args:
        pairs (dict): Pair positioning data; the keys being a two-element
            tuple of lists of glyphnames, and the values being a two-element
            tuple of ``otTables.ValueRecord`` objects.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.
        valueFormat1: Force the "left" value records to the given format.
        valueFormat2: Force the "right" value records to the given format.

    Returns:
        A ``otTables.PairPos`` object.
    """
    coverage = set()
    classDef1 = ClassDefBuilder(useClass0=True)
    classDef2 = ClassDefBuilder(useClass0=False)
    for gc1, gc2 in sorted(pairs):
        coverage.update(gc1)
        classDef1.add(gc1)
        classDef2.add(gc2)
    self = ot.PairPos()
    self.Format = 2
    valueFormat1 = self.ValueFormat1 = _getValueFormat(valueFormat1, pairs.values(), 0)
    valueFormat2 = self.ValueFormat2 = _getValueFormat(valueFormat2, pairs.values(), 1)
    self.Coverage = buildCoverage(coverage, glyphMap)
    self.ClassDef1 = classDef1.build()
    self.ClassDef2 = classDef2.build()
    classes1 = classDef1.classes()
    classes2 = classDef2.classes()
    self.Class1Record = []
    for c1 in classes1:
        rec1 = ot.Class1Record()
        rec1.Class2Record = []
        self.Class1Record.append(rec1)
        for c2 in classes2:
            rec2 = ot.Class2Record()
            val1, val2 = pairs.get((c1, c2), (None, None))
            rec2.Value1 = (
                ValueRecord(src=val1, valueFormat=valueFormat1)
                if valueFormat1
                else None
            )
            rec2.Value2 = (
                ValueRecord(src=val2, valueFormat=valueFormat2)
                if valueFormat2
                else None
            )
            rec1.Class2Record.append(rec2)
    self.Class1Count = len(self.Class1Record)
    self.Class2Count = len(classes2)
    return self


def buildPairPosGlyphs(pairs, glyphMap):
    """Builds a list of glyph-based pair adjustment (GPOS2 format 1) subtables.

    This organises a list of pair positioning adjustments into subtables based
    on common value record formats.

    Note that if you are implementing a layout compiler, you may find it more
    flexible to use
    :py:class:`fontTools.otlLib.lookupBuilders.PairPosBuilder`
    instead.

    Example::

        pairs = {
            ("K", "W"): ( buildValue(xAdvance=+5), buildValue() ),
            ("K", "V"): ( buildValue(xAdvance=+5), buildValue() ),
            # ...
        }

        subtables = buildPairPosGlyphs(pairs, font.getReverseGlyphMap())

    Args:
        pairs (dict): Pair positioning data; the keys being a two-element
            tuple of glyphnames, and the values being a two-element
            tuple of ``otTables.ValueRecord`` objects.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns:
        A list of ``otTables.PairPos`` objects.
    """

    p = {}  # (formatA, formatB) --> {(glyphA, glyphB): (valA, valB)}
    for (glyphA, glyphB), (valA, valB) in pairs.items():
        formatA = valA.getFormat() if valA is not None else 0
        formatB = valB.getFormat() if valB is not None else 0
        pos = p.setdefault((formatA, formatB), {})
        pos[(glyphA, glyphB)] = (valA, valB)
    return [
        buildPairPosGlyphsSubtable(pos, glyphMap, formatA, formatB)
        for ((formatA, formatB), pos) in sorted(p.items())
    ]


def buildPairPosGlyphsSubtable(pairs, glyphMap, valueFormat1=None, valueFormat2=None):
    """Builds a single glyph-based pair adjustment (GPOS2 format 1) subtable.

    This builds a PairPos subtable from a dictionary of glyph pairs and
    their positioning adjustments. See also :func:`buildPairPosGlyphs`.

    Note that if you are implementing a layout compiler, you may find it more
    flexible to use
    :py:class:`fontTools.otlLib.lookupBuilders.PairPosBuilder` instead.

    Example::

        pairs = {
            ("K", "W"): ( buildValue(xAdvance=+5), buildValue() ),
            ("K", "V"): ( buildValue(xAdvance=+5), buildValue() ),
            # ...
        }

        pairpos = buildPairPosGlyphsSubtable(pairs, font.getReverseGlyphMap())

    Args:
        pairs (dict): Pair positioning data; the keys being a two-element
            tuple of glyphnames, and the values being a two-element
            tuple of ``otTables.ValueRecord`` objects.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.
        valueFormat1: Force the "left" value records to the given format.
        valueFormat2: Force the "right" value records to the given format.

    Returns:
        A ``otTables.PairPos`` object.
    """
    self = ot.PairPos()
    self.Format = 1
    valueFormat1 = self.ValueFormat1 = _getValueFormat(valueFormat1, pairs.values(), 0)
    valueFormat2 = self.ValueFormat2 = _getValueFormat(valueFormat2, pairs.values(), 1)
    p = {}
    for (glyphA, glyphB), (valA, valB) in pairs.items():
        p.setdefault(glyphA, []).append((glyphB, valA, valB))
    self.Coverage = buildCoverage({g for g, _ in pairs.keys()}, glyphMap)
    self.PairSet = []
    for glyph in self.Coverage.glyphs:
        ps = ot.PairSet()
        ps.PairValueRecord = []
        self.PairSet.append(ps)
        for glyph2, val1, val2 in sorted(p[glyph], key=lambda x: glyphMap[x[0]]):
            pvr = ot.PairValueRecord()
            pvr.SecondGlyph = glyph2
            pvr.Value1 = (
                ValueRecord(src=val1, valueFormat=valueFormat1)
                if valueFormat1
                else None
            )
            pvr.Value2 = (
                ValueRecord(src=val2, valueFormat=valueFormat2)
                if valueFormat2
                else None
            )
            ps.PairValueRecord.append(pvr)
        ps.PairValueCount = len(ps.PairValueRecord)
    self.PairSetCount = len(self.PairSet)
    return self


def buildSinglePos(mapping, glyphMap):
    """Builds a list of single adjustment (GPOS1) subtables.

    This builds a list of SinglePos subtables from a dictionary of glyph
    names and their positioning adjustments. The format of the subtables are
    determined to optimize the size of the resulting subtables.
    See also :func:`buildSinglePosSubtable`.

    Note that if you are implementing a layout compiler, you may find it more
    flexible to use
    :py:class:`fontTools.otlLib.lookupBuilders.SinglePosBuilder` instead.

    Example::

        mapping = {
            "V": buildValue({ "xAdvance" : +5 }),
            # ...
        }

        subtables = buildSinglePos(pairs, font.getReverseGlyphMap())

    Args:
        mapping (dict): A mapping between glyphnames and
            ``otTables.ValueRecord`` objects.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns:
        A list of ``otTables.SinglePos`` objects.
    """
    result, handled = [], set()
    # In SinglePos format 1, the covered glyphs all share the same ValueRecord.
    # In format 2, each glyph has its own ValueRecord, but these records
    # all have the same properties (eg., all have an X but no Y placement).
    coverages, masks, values = {}, {}, {}
    for glyph, value in mapping.items():
        key = _getSinglePosValueKey(value)
        coverages.setdefault(key, []).append(glyph)
        masks.setdefault(key[0], []).append(key)
        values[key] = value

    # If a ValueRecord is shared between multiple glyphs, we generate
    # a SinglePos format 1 subtable; that is the most compact form.
    for key, glyphs in coverages.items():
        # 5 ushorts is the length of introducing another sublookup
        if len(glyphs) * _getSinglePosValueSize(key) > 5:
            format1Mapping = {g: values[key] for g in glyphs}
            result.append(buildSinglePosSubtable(format1Mapping, glyphMap))
            handled.add(key)

    # In the remaining ValueRecords, look for those whose valueFormat
    # (the set of used properties) is shared between multiple records.
    # These will get encoded in format 2.
    for valueFormat, keys in masks.items():
        f2 = [k for k in keys if k not in handled]
        if len(f2) > 1:
            format2Mapping = {}
            for k in f2:
                format2Mapping.update((g, values[k]) for g in coverages[k])
            result.append(buildSinglePosSubtable(format2Mapping, glyphMap))
            handled.update(f2)

    # The remaining ValueRecords are only used by a few glyphs, normally
    # one. We encode these in format 1 again.
    for key, glyphs in coverages.items():
        if key not in handled:
            for g in glyphs:
                st = buildSinglePosSubtable({g: values[key]}, glyphMap)
            result.append(st)

    # When the OpenType layout engine traverses the subtables, it will
    # stop after the first matching subtable.  Therefore, we sort the
    # resulting subtables by decreasing coverage size; this increases
    # the chance that the layout engine can do an early exit. (Of course,
    # this would only be true if all glyphs were equally frequent, which
    # is not really the case; but we do not know their distribution).
    # If two subtables cover the same number of glyphs, we sort them
    # by glyph ID so that our output is deterministic.
    result.sort(key=lambda t: _getSinglePosTableKey(t, glyphMap))
    return result


def buildSinglePosSubtable(values, glyphMap):
    """Builds a single adjustment (GPOS1) subtable.

    This builds a list of SinglePos subtables from a dictionary of glyph
    names and their positioning adjustments. The format of the subtable is
    determined to optimize the size of the output.
    See also :func:`buildSinglePos`.

    Note that if you are implementing a layout compiler, you may find it more
    flexible to use
    :py:class:`fontTools.otlLib.lookupBuilders.SinglePosBuilder` instead.

    Example::

        mapping = {
            "V": buildValue({ "xAdvance" : +5 }),
            # ...
        }

        subtable = buildSinglePos(pairs, font.getReverseGlyphMap())

    Args:
        mapping (dict): A mapping between glyphnames and
            ``otTables.ValueRecord`` objects.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns:
        A ``otTables.SinglePos`` object.
    """
    self = ot.SinglePos()
    self.Coverage = buildCoverage(values.keys(), glyphMap)
    valueFormat = self.ValueFormat = reduce(
        int.__or__, [v.getFormat() for v in values.values()], 0
    )
    valueRecords = [
        ValueRecord(src=values[g], valueFormat=valueFormat)
        for g in self.Coverage.glyphs
    ]
    if all(v == valueRecords[0] for v in valueRecords):
        self.Format = 1
        if self.ValueFormat != 0:
            self.Value = valueRecords[0]
        else:
            self.Value = None
    else:
        self.Format = 2
        self.Value = valueRecords
        self.ValueCount = len(self.Value)
    return self


def _getSinglePosTableKey(subtable, glyphMap):
    assert isinstance(subtable, ot.SinglePos), subtable
    glyphs = subtable.Coverage.glyphs
    return (-len(glyphs), glyphMap[glyphs[0]])


def _getSinglePosValueKey(valueRecord):
    # otBase.ValueRecord --> (2, ("YPlacement": 12))
    assert isinstance(valueRecord, ValueRecord), valueRecord
    valueFormat, result = 0, []
    for name, value in valueRecord.__dict__.items():
        if isinstance(value, ot.Device):
            result.append((name, _makeDeviceTuple(value)))
        else:
            result.append((name, value))
        valueFormat |= valueRecordFormatDict[name][0]
    result.sort()
    result.insert(0, valueFormat)
    return tuple(result)


_DeviceTuple = namedtuple("_DeviceTuple", "DeltaFormat StartSize EndSize DeltaValue")


def _makeDeviceTuple(device):
    # otTables.Device --> tuple, for making device tables unique
    return _DeviceTuple(
        device.DeltaFormat,
        device.StartSize,
        device.EndSize,
        () if device.DeltaFormat & 0x8000 else tuple(device.DeltaValue),
    )


def _getSinglePosValueSize(valueKey):
    # Returns how many ushorts this valueKey (short form of ValueRecord) takes up
    count = 0
    for _, v in valueKey[1:]:
        if isinstance(v, _DeviceTuple):
            count += len(v.DeltaValue) + 3
        else:
            count += 1
    return count


def buildValue(value):
    """Builds a positioning value record.

    Value records are used to specify coordinates and adjustments for
    positioning and attaching glyphs. Many of the positioning functions
    in this library take ``otTables.ValueRecord`` objects as arguments.
    This function builds value records from dictionaries.

    Args:
        value (dict): A dictionary with zero or more of the following keys:
            - ``xPlacement``
            - ``yPlacement``
            - ``xAdvance``
            - ``yAdvance``
            - ``xPlaDevice``
            - ``yPlaDevice``
            - ``xAdvDevice``
            - ``yAdvDevice``

    Returns:
        An ``otTables.ValueRecord`` object.
    """
    self = ValueRecord()
    for k, v in value.items():
        setattr(self, k, v)
    return self


# GDEF


def buildAttachList(attachPoints, glyphMap):
    """Builds an AttachList subtable.

    A GDEF table may contain an Attachment Point List table (AttachList)
    which stores the contour indices of attachment points for glyphs with
    attachment points. This routine builds AttachList subtables.

    Args:
        attachPoints (dict): A mapping between glyph names and a list of
            contour indices.

    Returns:
        An ``otTables.AttachList`` object if attachment points are supplied,
            or ``None`` otherwise.
    """
    if not attachPoints:
        return None
    self = ot.AttachList()
    self.Coverage = buildCoverage(attachPoints.keys(), glyphMap)
    self.AttachPoint = [buildAttachPoint(attachPoints[g]) for g in self.Coverage.glyphs]
    self.GlyphCount = len(self.AttachPoint)
    return self


def buildAttachPoint(points):
    # [4, 23, 41] --> otTables.AttachPoint
    # Only used by above.
    if not points:
        return None
    self = ot.AttachPoint()
    self.PointIndex = sorted(set(points))
    self.PointCount = len(self.PointIndex)
    return self


def buildCaretValueForCoord(coord):
    # 500 --> otTables.CaretValue, format 1
    # (500, DeviceTable) --> otTables.CaretValue, format 3
    self = ot.CaretValue()
    if isinstance(coord, tuple):
        self.Format = 3
        self.Coordinate, self.DeviceTable = coord
    else:
        self.Format = 1
        self.Coordinate = coord
    return self


def buildCaretValueForPoint(point):
    # 4 --> otTables.CaretValue, format 2
    self = ot.CaretValue()
    self.Format = 2
    self.CaretValuePoint = point
    return self


def buildLigCaretList(coords, points, glyphMap):
    """Builds a ligature caret list table.

    Ligatures appear as a single glyph representing multiple characters; however
    when, for example, editing text containing a ``f_i`` ligature, the user may
    want to place the cursor between the ``f`` and the ``i``. The ligature caret
    list in the GDEF table specifies the position to display the "caret" (the
    character insertion indicator, typically a flashing vertical bar) "inside"
    the ligature to represent an insertion point. The insertion positions may
    be specified either by coordinate or by contour point.

    Example::

        coords = {
            "f_f_i": [300, 600] # f|fi cursor at 300 units, ff|i cursor at 600.
        }
        points = {
            "c_t": [28] # c|t cursor appears at coordinate of contour point 28.
        }
        ligcaretlist = buildLigCaretList(coords, points, font.getReverseGlyphMap())

    Args:
        coords: A mapping between glyph names and a list of coordinates for
            the insertion point of each ligature component after the first one.
        points: A mapping between glyph names and a list of contour points for
            the insertion point of each ligature component after the first one.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns:
        A ``otTables.LigCaretList`` object if any carets are present, or
            ``None`` otherwise."""
    glyphs = set(coords.keys()) if coords else set()
    if points:
        glyphs.update(points.keys())
    carets = {g: buildLigGlyph(coords.get(g), points.get(g)) for g in glyphs}
    carets = {g: c for g, c in carets.items() if c is not None}
    if not carets:
        return None
    self = ot.LigCaretList()
    self.Coverage = buildCoverage(carets.keys(), glyphMap)
    self.LigGlyph = [carets[g] for g in self.Coverage.glyphs]
    self.LigGlyphCount = len(self.LigGlyph)
    return self


def buildLigGlyph(coords, points):
    # ([500], [4]) --> otTables.LigGlyph; None for empty coords/points
    carets = []
    if coords:
        coords = sorted(coords, key=lambda c: c[0] if isinstance(c, tuple) else c)
        carets.extend([buildCaretValueForCoord(c) for c in coords])
    if points:
        carets.extend([buildCaretValueForPoint(p) for p in sorted(points)])
    if not carets:
        return None
    self = ot.LigGlyph()
    self.CaretValue = carets
    self.CaretCount = len(self.CaretValue)
    return self


def buildMarkGlyphSetsDef(markSets, glyphMap):
    """Builds a mark glyph sets definition table.

    OpenType Layout lookups may choose to use mark filtering sets to consider
    or ignore particular combinations of marks. These sets are specified by
    setting a flag on the lookup, but the mark filtering sets are defined in
    the ``GDEF`` table. This routine builds the subtable containing the mark
    glyph set definitions.

    Example::

        set0 = set("acute", "grave")
        set1 = set("caron", "grave")

        markglyphsets = buildMarkGlyphSetsDef([set0, set1], font.getReverseGlyphMap())

    Args:

        markSets: A list of sets of glyphnames.
        glyphMap: a glyph name to ID map, typically returned from
            ``font.getReverseGlyphMap()``.

    Returns
        An ``otTables.MarkGlyphSetsDef`` object.
    """
    if not markSets:
        return None
    self = ot.MarkGlyphSetsDef()
    self.MarkSetTableFormat = 1
    self.Coverage = [buildCoverage(m, glyphMap) for m in markSets]
    self.MarkSetCount = len(self.Coverage)
    return self


class ClassDefBuilder(object):
    """Helper for building ClassDef tables."""

    def __init__(self, useClass0):
        self.classes_ = set()
        self.glyphs_ = {}
        self.useClass0_ = useClass0

    def canAdd(self, glyphs):
        if isinstance(glyphs, (set, frozenset)):
            glyphs = sorted(glyphs)
        glyphs = tuple(glyphs)
        if glyphs in self.classes_:
            return True
        for glyph in glyphs:
            if glyph in self.glyphs_:
                return False
        return True

    def add(self, glyphs):
        if isinstance(glyphs, (set, frozenset)):
            glyphs = sorted(glyphs)
        glyphs = tuple(glyphs)
        if glyphs in self.classes_:
            return
        self.classes_.add(glyphs)
        for glyph in glyphs:
            if glyph in self.glyphs_:
                raise OpenTypeLibError(
                    f"Glyph {glyph} is already present in class.", None
                )
            self.glyphs_[glyph] = glyphs

    def classes(self):
        # In ClassDef1 tables, class id #0 does not need to be encoded
        # because zero is the default. Therefore, we use id #0 for the
        # glyph class that has the largest number of members. However,
        # in other tables than ClassDef1, 0 means "every other glyph"
        # so we should not use that ID for any real glyph classes;
        # we implement this by inserting an empty set at position 0.
        #
        # TODO: Instead of counting the number of glyphs in each class,
        # we should determine the encoded size. If the glyphs in a large
        # class form a contiguous range, the encoding is actually quite
        # compact, whereas a non-contiguous set might need a lot of bytes
        # in the output file. We don't get this right with the key below.
        result = sorted(self.classes_, key=lambda s: (-len(s), s))
        if not self.useClass0_:
            result.insert(0, frozenset())
        return result

    def build(self):
        glyphClasses = {}
        for classID, glyphs in enumerate(self.classes()):
            if classID == 0:
                continue
            for glyph in glyphs:
                glyphClasses[glyph] = classID
        classDef = ot.ClassDef()
        classDef.classDefs = glyphClasses
        return classDef


AXIS_VALUE_NEGATIVE_INFINITY = fixedToFloat(-0x80000000, 16)
AXIS_VALUE_POSITIVE_INFINITY = fixedToFloat(0x7FFFFFFF, 16)

STATName = Union[int, str, Dict[str, str]]
"""A raw name ID, English name, or multilingual name."""


def buildStatTable(
    ttFont: TTFont,
    axes,
    locations=None,
    elidedFallbackName: Union[STATName, STATNameStatement] = 2,
    windowsNames: bool = True,
    macNames: bool = True,
) -> None:
    """Add a 'STAT' table to 'ttFont'.

    'axes' is a list of dictionaries describing axes and their
    values.

    Example::

        axes = [
            dict(
                tag="wght",
                name="Weight",
                ordering=0,  # optional
                values=[
                    dict(value=100, name='Thin'),
                    dict(value=300, name='Light'),
                    dict(value=400, name='Regular', flags=0x2),
                    dict(value=900, name='Black'),
                ],
            )
        ]

    Each axis dict must have 'tag' and 'name' items. 'tag' maps
    to the 'AxisTag' field. 'name' can be a name ID (int), a string,
    or a dictionary containing multilingual names (see the
    addMultilingualName() name table method), and will translate to
    the AxisNameID field.

    An axis dict may contain an 'ordering' item that maps to the
    AxisOrdering field. If omitted, the order of the axes list is
    used to calculate AxisOrdering fields.

    The axis dict may contain a 'values' item, which is a list of
    dictionaries describing AxisValue records belonging to this axis.

    Each value dict must have a 'name' item, which can be a name ID
    (int), a string, or a dictionary containing multilingual names,
    like the axis name. It translates to the ValueNameID field.

    Optionally the value dict can contain a 'flags' item. It maps to
    the AxisValue Flags field, and will be 0 when omitted.

    The format of the AxisValue is determined by the remaining contents
    of the value dictionary:

    If the value dict contains a 'value' item, an AxisValue record
    Format 1 is created. If in addition to the 'value' item it contains
    a 'linkedValue' item, an AxisValue record Format 3 is built.

    If the value dict contains a 'nominalValue' item, an AxisValue
    record Format 2 is built. Optionally it may contain 'rangeMinValue'
    and 'rangeMaxValue' items. These map to -Infinity and +Infinity
    respectively if omitted.

    You cannot specify Format 4 AxisValue tables this way, as they are
    not tied to a single axis, and specify a name for a location that
    is defined by multiple axes values. Instead, you need to supply the
    'locations' argument.

    The optional 'locations' argument specifies AxisValue Format 4
    tables. It should be a list of dicts, where each dict has a 'name'
    item, which works just like the value dicts above, an optional
    'flags' item (defaulting to 0x0), and a 'location' dict. A
    location dict key is an axis tag, and the associated value is the
    location on the specified axis. They map to the AxisIndex and Value
    fields of the AxisValueRecord.

    Example::

        locations = [
            dict(name='Regular ABCD', location=dict(wght=300, ABCD=100)),
            dict(name='Bold ABCD XYZ', location=dict(wght=600, ABCD=200)),
        ]

    The optional 'elidedFallbackName' argument can be a name ID (int),
    a string, a dictionary containing multilingual names, or a list of
    STATNameStatements. It translates to the ElidedFallbackNameID field.

    The 'ttFont' argument must be a TTFont instance that already has a
    'name' table. If a 'STAT' table already exists, it will be
    overwritten by the newly created one.
    """
    ttFont["STAT"] = ttLib.newTable("STAT")
    statTable = ttFont["STAT"].table = ot.STAT()
    statTable.ElidedFallbackNameID = _addName(
        ttFont, elidedFallbackName, windows=windowsNames, mac=macNames
    )

    # 'locations' contains data for AxisValue Format 4
    axisRecords, axisValues = _buildAxisRecords(
        axes, ttFont, windowsNames=windowsNames, macNames=macNames
    )
    if not locations:
        statTable.Version = 0x00010001
    else:
        # We'll be adding Format 4 AxisValue records, which
        # requires a higher table version
        statTable.Version = 0x00010002
        multiAxisValues = _buildAxisValuesFormat4(
            locations, axes, ttFont, windowsNames=windowsNames, macNames=macNames
        )
        axisValues = multiAxisValues + axisValues
    ttFont["name"].names.sort()

    # Store AxisRecords
    axisRecordArray = ot.AxisRecordArray()
    axisRecordArray.Axis = axisRecords
    # XXX these should not be hard-coded but computed automatically
    statTable.DesignAxisRecordSize = 8
    statTable.DesignAxisRecord = axisRecordArray
    statTable.DesignAxisCount = len(axisRecords)

    statTable.AxisValueCount = 0
    statTable.AxisValueArray = None
    if axisValues:
        # Store AxisValueRecords
        axisValueArray = ot.AxisValueArray()
        axisValueArray.AxisValue = axisValues
        statTable.AxisValueArray = axisValueArray
        statTable.AxisValueCount = len(axisValues)


def _buildAxisRecords(axes, ttFont, windowsNames=True, macNames=True):
    axisRecords = []
    axisValues = []
    for axisRecordIndex, axisDict in enumerate(axes):
        axis = ot.AxisRecord()
        axis.AxisTag = axisDict["tag"]
        axis.AxisNameID = _addName(
            ttFont, axisDict["name"], 256, windows=windowsNames, mac=macNames
        )
        axis.AxisOrdering = axisDict.get("ordering", axisRecordIndex)
        axisRecords.append(axis)

        for axisVal in axisDict.get("values", ()):
            axisValRec = ot.AxisValue()
            axisValRec.AxisIndex = axisRecordIndex
            axisValRec.Flags = axisVal.get("flags", 0)
            axisValRec.ValueNameID = _addName(
                ttFont, axisVal["name"], windows=windowsNames, mac=macNames
            )

            if "value" in axisVal:
                axisValRec.Value = axisVal["value"]
                if "linkedValue" in axisVal:
                    axisValRec.Format = 3
                    axisValRec.LinkedValue = axisVal["linkedValue"]
                else:
                    axisValRec.Format = 1
            elif "nominalValue" in axisVal:
                axisValRec.Format = 2
                axisValRec.NominalValue = axisVal["nominalValue"]
                axisValRec.RangeMinValue = axisVal.get(
                    "rangeMinValue", AXIS_VALUE_NEGATIVE_INFINITY
                )
                axisValRec.RangeMaxValue = axisVal.get(
                    "rangeMaxValue", AXIS_VALUE_POSITIVE_INFINITY
                )
            else:
                raise ValueError("Can't determine format for AxisValue")

            axisValues.append(axisValRec)
    return axisRecords, axisValues


def _buildAxisValuesFormat4(locations, axes, ttFont, windowsNames=True, macNames=True):
    axisTagToIndex = {}
    for axisRecordIndex, axisDict in enumerate(axes):
        axisTagToIndex[axisDict["tag"]] = axisRecordIndex

    axisValues = []
    for axisLocationDict in locations:
        axisValRec = ot.AxisValue()
        axisValRec.Format = 4
        axisValRec.ValueNameID = _addName(
            ttFont, axisLocationDict["name"], windows=windowsNames, mac=macNames
        )
        axisValRec.Flags = axisLocationDict.get("flags", 0)
        axisValueRecords = []
        for tag, value in axisLocationDict["location"].items():
            avr = ot.AxisValueRecord()
            avr.AxisIndex = axisTagToIndex[tag]
            avr.Value = value
            axisValueRecords.append(avr)
        axisValueRecords.sort(key=lambda avr: avr.AxisIndex)
        axisValRec.AxisCount = len(axisValueRecords)
        axisValRec.AxisValueRecord = axisValueRecords
        axisValues.append(axisValRec)
    return axisValues


def _addName(
    ttFont: TTFont,
    value: Union[STATName, STATNameStatement],
    minNameID: int = 0,
    windows: bool = True,
    mac: bool = True,
) -> int:
    nameTable = ttFont["name"]
    if isinstance(value, int):
        # Already a nameID
        return value
    if isinstance(value, str):
        names = dict(en=value)
    elif isinstance(value, dict):
        names = value
    elif isinstance(value, list):
        nameID = nameTable._findUnusedNameID()
        for nameRecord in value:
            if isinstance(nameRecord, STATNameStatement):
                nameTable.setName(
                    nameRecord.string,
                    nameID,
                    nameRecord.platformID,
                    nameRecord.platEncID,
                    nameRecord.langID,
                )
            else:
                raise TypeError("value must be a list of STATNameStatements")
        return nameID
    else:
        raise TypeError("value must be int, str, dict or list")
    return nameTable.addMultilingualName(
        names, ttFont=ttFont, windows=windows, mac=mac, minNameID=minNameID
    )


def buildMathTable(
    ttFont,
    constants=None,
    italicsCorrections=None,
    topAccentAttachments=None,
    extendedShapes=None,
    mathKerns=None,
    minConnectorOverlap=0,
    vertGlyphVariants=None,
    horizGlyphVariants=None,
    vertGlyphAssembly=None,
    horizGlyphAssembly=None,
):
    """
    Add a 'MATH' table to 'ttFont'.

    'constants' is a dictionary of math constants. The keys are the constant
    names from the MATH table specification (with capital first letter), and the
    values are the constant values as numbers.

    'italicsCorrections' is a dictionary of italic corrections. The keys are the
    glyph names, and the values are the italic corrections as numbers.

    'topAccentAttachments' is a dictionary of top accent attachments. The keys
    are the glyph names, and the values are the top accent horizontal positions
    as numbers.

    'extendedShapes' is a set of extended shape glyphs.

    'mathKerns' is a dictionary of math kerns. The keys are the glyph names, and
    the values are dictionaries. The keys of these dictionaries are the side
    names ('TopRight', 'TopLeft', 'BottomRight', 'BottomLeft'), and the values
    are tuples of two lists. The first list contains the correction heights as
    numbers, and the second list contains the kern values as numbers.

    'minConnectorOverlap' is the minimum connector overlap as a number.

    'vertGlyphVariants' is a dictionary of vertical glyph variants. The keys are
    the glyph names, and the values are tuples of glyph name and full advance height.

    'horizGlyphVariants' is a dictionary of horizontal glyph variants. The keys
    are the glyph names, and the values are tuples of glyph name and full
    advance width.

    'vertGlyphAssembly' is a dictionary of vertical glyph assemblies. The keys
    are the glyph names, and the values are tuples of assembly parts and italics
    correction. The assembly parts are tuples of glyph name, flags, start
    connector length, end connector length, and full advance height.

    'horizGlyphAssembly' is a dictionary of horizontal glyph assemblies. The
    keys are the glyph names, and the values are tuples of assembly parts
    and italics correction. The assembly parts are tuples of glyph name, flags,
    start connector length, end connector length, and full advance width.

    Where a number is expected, an integer or a float can be used. The floats
    will be rounded.

    Example::

        constants = {
            "ScriptPercentScaleDown": 70,
            "ScriptScriptPercentScaleDown": 50,
            "DelimitedSubFormulaMinHeight": 24,
            "DisplayOperatorMinHeight": 60,
            ...
        }
        italicsCorrections = {
            "fitalic-math": 100,
            "fbolditalic-math": 120,
            ...
        }
        topAccentAttachments = {
            "circumflexcomb": 500,
            "acutecomb": 400,
            "A": 300,
            "B": 340,
            ...
        }
        extendedShapes = {"parenleft", "parenright", ...}
        mathKerns = {
            "A": {
                "TopRight": ([-50, -100], [10, 20, 30]),
                "TopLeft": ([50, 100], [10, 20, 30]),
                ...
            },
            ...
        }
        vertGlyphVariants = {
            "parenleft": [("parenleft", 700), ("parenleft.size1", 1000), ...],
            "parenright": [("parenright", 700), ("parenright.size1", 1000), ...],
            ...
        }
        vertGlyphAssembly = {
            "braceleft": [
                (
                    ("braceleft.bottom", 0, 0, 200, 500),
                    ("braceleft.extender", 1, 200, 200, 200)),
                    ("braceleft.middle", 0, 100, 100, 700),
                    ("braceleft.extender", 1, 200, 200, 200),
                    ("braceleft.top", 0, 200, 0, 500),
                ),
                100,
            ],
            ...
        }
    """
    glyphMap = ttFont.getReverseGlyphMap()

    ttFont["MATH"] = math = ttLib.newTable("MATH")
    math.table = table = ot.MATH()
    table.Version = 0x00010000
    table.populateDefaults()

    table.MathConstants = _buildMathConstants(constants)
    table.MathGlyphInfo = _buildMathGlyphInfo(
        glyphMap,
        italicsCorrections,
        topAccentAttachments,
        extendedShapes,
        mathKerns,
    )
    table.MathVariants = _buildMathVariants(
        glyphMap,
        minConnectorOverlap,
        vertGlyphVariants,
        horizGlyphVariants,
        vertGlyphAssembly,
        horizGlyphAssembly,
    )


def _buildMathConstants(constants):
    if not constants:
        return None

    mathConstants = ot.MathConstants()
    for conv in mathConstants.getConverters():
        value = otRound(constants.get(conv.name, 0))
        if conv.tableClass:
            assert issubclass(conv.tableClass, ot.MathValueRecord)
            value = _mathValueRecord(value)
        setattr(mathConstants, conv.name, value)
    return mathConstants


def _buildMathGlyphInfo(
    glyphMap,
    italicsCorrections,
    topAccentAttachments,
    extendedShapes,
    mathKerns,
):
    if not any([extendedShapes, italicsCorrections, topAccentAttachments, mathKerns]):
        return None

    info = ot.MathGlyphInfo()
    info.populateDefaults()

    if italicsCorrections:
        coverage = buildCoverage(italicsCorrections.keys(), glyphMap)
        info.MathItalicsCorrectionInfo = ot.MathItalicsCorrectionInfo()
        info.MathItalicsCorrectionInfo.Coverage = coverage
        info.MathItalicsCorrectionInfo.ItalicsCorrectionCount = len(coverage.glyphs)
        info.MathItalicsCorrectionInfo.ItalicsCorrection = [
            _mathValueRecord(italicsCorrections[n]) for n in coverage.glyphs
        ]

    if topAccentAttachments:
        coverage = buildCoverage(topAccentAttachments.keys(), glyphMap)
        info.MathTopAccentAttachment = ot.MathTopAccentAttachment()
        info.MathTopAccentAttachment.TopAccentCoverage = coverage
        info.MathTopAccentAttachment.TopAccentAttachmentCount = len(coverage.glyphs)
        info.MathTopAccentAttachment.TopAccentAttachment = [
            _mathValueRecord(topAccentAttachments[n]) for n in coverage.glyphs
        ]

    if extendedShapes:
        info.ExtendedShapeCoverage = buildCoverage(extendedShapes, glyphMap)

    if mathKerns:
        coverage = buildCoverage(mathKerns.keys(), glyphMap)
        info.MathKernInfo = ot.MathKernInfo()
        info.MathKernInfo.MathKernCoverage = coverage
        info.MathKernInfo.MathKernCount = len(coverage.glyphs)
        info.MathKernInfo.MathKernInfoRecords = []
        for glyph in coverage.glyphs:
            record = ot.MathKernInfoRecord()
            for side in {"TopRight", "TopLeft", "BottomRight", "BottomLeft"}:
                if side in mathKerns[glyph]:
                    correctionHeights, kernValues = mathKerns[glyph][side]
                    assert len(correctionHeights) == len(kernValues) - 1
                    kern = ot.MathKern()
                    kern.HeightCount = len(correctionHeights)
                    kern.CorrectionHeight = [
                        _mathValueRecord(h) for h in correctionHeights
                    ]
                    kern.KernValue = [_mathValueRecord(v) for v in kernValues]
                    setattr(record, f"{side}MathKern", kern)
            info.MathKernInfo.MathKernInfoRecords.append(record)

    return info


def _buildMathVariants(
    glyphMap,
    minConnectorOverlap,
    vertGlyphVariants,
    horizGlyphVariants,
    vertGlyphAssembly,
    horizGlyphAssembly,
):
    if not any(
        [vertGlyphVariants, horizGlyphVariants, vertGlyphAssembly, horizGlyphAssembly]
    ):
        return None

    variants = ot.MathVariants()
    variants.populateDefaults()

    variants.MinConnectorOverlap = minConnectorOverlap

    if vertGlyphVariants or vertGlyphAssembly:
        variants.VertGlyphCoverage, variants.VertGlyphConstruction = (
            _buildMathGlyphConstruction(
                glyphMap,
                vertGlyphVariants,
                vertGlyphAssembly,
            )
        )

    if horizGlyphVariants or horizGlyphAssembly:
        variants.HorizGlyphCoverage, variants.HorizGlyphConstruction = (
            _buildMathGlyphConstruction(
                glyphMap,
                horizGlyphVariants,
                horizGlyphAssembly,
            )
        )

    return variants


def _buildMathGlyphConstruction(glyphMap, variants, assemblies):
    glyphs = set()
    if variants:
        glyphs.update(variants.keys())
    if assemblies:
        glyphs.update(assemblies.keys())
    coverage = buildCoverage(glyphs, glyphMap)
    constructions = []

    for glyphName in coverage.glyphs:
        construction = ot.MathGlyphConstruction()
        construction.populateDefaults()

        if variants and glyphName in variants:
            construction.VariantCount = len(variants[glyphName])
            construction.MathGlyphVariantRecord = []
            for variantName, advance in variants[glyphName]:
                record = ot.MathGlyphVariantRecord()
                record.VariantGlyph = variantName
                record.AdvanceMeasurement = otRound(advance)
                construction.MathGlyphVariantRecord.append(record)

        if assemblies and glyphName in assemblies:
            parts, ic = assemblies[glyphName]
            construction.GlyphAssembly = ot.GlyphAssembly()
            construction.GlyphAssembly.ItalicsCorrection = _mathValueRecord(ic)
            construction.GlyphAssembly.PartCount = len(parts)
            construction.GlyphAssembly.PartRecords = []
            for part in parts:
                part_name, flags, start, end, advance = part
                record = ot.GlyphPartRecord()
                record.glyph = part_name
                record.PartFlags = int(flags)
                record.StartConnectorLength = otRound(start)
                record.EndConnectorLength = otRound(end)
                record.FullAdvance = otRound(advance)
                construction.GlyphAssembly.PartRecords.append(record)

        constructions.append(construction)

    return coverage, constructions


def _mathValueRecord(value):
    value_record = ot.MathValueRecord()
    value_record.Value = otRound(value)
    return value_record