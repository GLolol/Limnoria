###
# Copyright (c) 2002-2004, Jeremiah Fincher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

"""
Simple utility functions.
"""

__revision__ = "$Id$"

import supybot.fix as fix

import os
import re
import sys
import md5
import new
import sha
import sets
import time
import types
import random
import shutil
import socket
import string
import sgmllib
import compiler
import textwrap
import UserDict
import itertools
import traceback
import htmlentitydefs
from itertools import imap, ifilter

from supybot.structures import TwoWayDictionary

curry = new.instancemethod

def normalizeWhitespace(s):
    """Normalizes the whitespace in a string; \s+ becomes one space."""
    return ' '.join(s.split())

class HtmlToText(sgmllib.SGMLParser):
    """Taken from some eff-bot code on c.l.p."""
    entitydefs = htmlentitydefs.entitydefs.copy()
    entitydefs['nbsp'] = ' '
    def __init__(self, tagReplace=' '):
        self.data = []
        self.tagReplace = tagReplace
        sgmllib.SGMLParser.__init__(self)

    def unknown_starttag(self, tag, attr):
        self.data.append(self.tagReplace)

    def unknown_endtag(self, tag):
        self.data.append(self.tagReplace)

    def handle_data(self, data):
        self.data.append(data)

    def getText(self):
        text = ''.join(self.data).strip()
        return normalizeWhitespace(text)

def htmlToText(s, tagReplace=' '):
    """Turns HTML into text.  tagReplace is a string to replace HTML tags with.
    """
    x = HtmlToText(tagReplace)
    x.feed(s)
    return x.getText()

def eachSubstring(s):
    """Returns every substring starting at the first index until the last."""
    for i in xrange(1, len(s)+1):
        yield s[:i]

def abbrev(strings, d=None):
    """Returns a dictionary mapping unambiguous abbreviations to full forms."""
    if len(strings) != len(set(strings)):
        raise ValueError, \
              'strings given to utils.abbrev have duplicates: %r' % strings
    if d is None:
        d = {}
    for s in strings:
        for abbreviation in eachSubstring(s):
            if abbreviation not in d:
                d[abbreviation] = s
            else:
                if abbreviation not in strings:
                    d[abbreviation] = None
    removals = []
    for key in d:
        if d[key] is None:
            removals.append(key)
    for key in removals:
        del d[key]
    return d

def timeElapsed(elapsed, short=False, leadingZeroes=False, years=True,
                weeks=True, days=True, hours=True, minutes=True, seconds=True):
    """Given <elapsed> seconds, returns a string with an English description of
    how much time as passed.  leadingZeroes determines whether 0 days, 0 hours,
    etc. will be printed; the others determine what larger time periods should
    be used.
    """
    ret = []
    def format(s, i):
        if i or leadingZeroes or ret:
            if short:
                ret.append('%s%s' % (i, s[0]))
            else:
                ret.append(nItems(s, i))
    elapsed = int(elapsed)
    assert years or weeks or days or \
           hours or minutes or seconds, 'One flag must be True'
    if years:
        (yrs, elapsed) = (elapsed // 31536000, elapsed % 31536000)
        format('year', yrs)
    if weeks:
        (wks, elapsed) = (elapsed // 604800, elapsed % 604800)
        format('week', wks)
    if days:
        (ds, elapsed) = (elapsed // 86400, elapsed % 86400)
        format('day', ds)
    if hours:
        (hrs, elapsed) = (elapsed // 3600, elapsed % 3600)
        format('hour', hrs)
    if minutes or seconds:
        (mins, secs) = (elapsed // 60, elapsed % 60)
        if leadingZeroes or mins:
            format('minute', mins)
        if seconds:
            leadingZeroes = True
            format('second', secs)
    if not ret:
        raise ValueError, 'Time difference not great enough to be noted.'
    if short:
        return ' '.join(ret)
    else:
        return commaAndify(ret)

def distance(s, t):
    """Returns the levenshtein edit distance between two strings."""
    n = len(s)
    m = len(t)
    if n == 0:
        return m
    elif m == 0:
        return n
    d = []
    for i in range(n+1):
        d.append([])
        for j in range(m+1):
            d[i].append(0)
            d[0][j] = j
        d[i][0] = i
    for i in range(1, n+1):
        cs = s[i-1]
        for j in range(1, m+1):
            ct = t[j-1]
            cost = int(cs != ct)
            d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+cost)
    return d[n][m]

_soundextrans = string.maketrans(string.ascii_uppercase,
                                 '01230120022455012623010202')
_notUpper = string.ascii.translate(string.ascii, string.ascii_uppercase)
def soundex(s, length=4):
    """Returns the soundex hash of a given string."""
    s = s.upper() # Make everything uppercase.
    s = s.translate(string.ascii, _notUpper) # Delete non-letters.
    if not s:
        raise ValueError, 'Invalid string for soundex: %s'
    firstChar = s[0] # Save the first character.
    s = s.translate(_soundextrans) # Convert to soundex numbers.
    s = s.lstrip(s[0]) # Remove all repeated first characters.
    L = [firstChar]
    for c in s:
        if c != L[-1]:
            L.append(c)
    L = [c for c in L if c != '0'] + (['0']*(length-1))
    s = ''.join(L)
    return length and s[:length] or s.rstrip('0')

def dqrepr(s):
    """Returns a repr() of s guaranteed to be in double quotes."""
    # The wankers-that-be decided not to use double-quotes anymore in 2.3.
    # return '"' + repr("'\x00" + s)[6:]
    return '"%s"' % s.encode('string_escape').replace('"', '\\"')

def quoted(s):
    """Returns a quoted s."""
    return '"%s"' % s

def _getSep(s):
    if len(s) < 2:
        raise ValueError, 'string given to _getSep is too short: %r' % s
    if s.startswith('m') or s.startswith('s'):
        separator = s[1]
    else:
        separator = s[0]
    if separator.isalnum() or separator in '{}[]()<>':
        raise ValueError, \
              'Invalid separator: separator must not be alphanumeric or in ' \
              '"{}[]()<>"'
    return separator

def _getSplitterRe(s):
    separator = _getSep(s)
    return re.compile(r'(?<!\\)%s' % re.escape(separator))
        
def perlReToPythonRe(s):
    """Converts a string representation of a Perl regular expression (i.e.,
    m/^foo$/i or /foo|bar/) to a Python regular expression.
    """
    sep = _getSep(s)
    splitter = _getSplitterRe(s)
    try:
        (kind, regexp, flags) = splitter.split(s)
    except ValueError: # Unpack list of wrong size.
        raise ValueError, 'Must be of the form m/.../ or /.../'
    regexp = regexp.replace('\\'+sep, sep)
    if kind not in ('', 'm'):
        raise ValueError, 'Invalid kind: must be in ("", "m")'
    flag = 0
    try:
        for c in flags.upper():
            flag |= getattr(re, c)
    except AttributeError:
        raise ValueError, 'Invalid flag: %s' % c
    try:
        return re.compile(regexp, flag)
    except re.error, e:
        raise ValueError, str(e)

def perlReToReplacer(s):
    """Converts a string representation of a Perl regular expression (i.e.,
    s/foo/bar/g or s/foo/bar/i) to a Python function doing the equivalent
    replacement.
    """
    sep = _getSep(s)
    splitter = _getSplitterRe(s)
    try:
        (kind, regexp, replace, flags) = splitter.split(s)
    except ValueError: # Unpack list of wrong size.
        raise ValueError, 'Must be of the form s/.../.../'
    regexp = regexp.replace('\x08', r'\b')
    replace = replace.replace('\\'+sep, sep)
    for i in xrange(10):
        replace = replace.replace(chr(i), r'\%s' % i)
    if kind != 's':
        raise ValueError, 'Invalid kind: must be "s"'
    g = False
    if 'g' in flags:
        g = True
        flags = filter('g'.__ne__, flags)
    r = perlReToPythonRe('/'.join(('', regexp, flags)))
    if g:
        return curry(r.sub, replace)
    else:
        return lambda s: r.sub(replace, s, 1)

_perlVarSubstituteRe = re.compile(r'\$\{([^}]+)\}|\$([a-zA-Z][a-zA-Z0-9]*)')
def perlVariableSubstitute(vars, text):
    def replacer(m):
        (braced, unbraced) = m.groups()
        var = braced or unbraced
        try:
            x = vars[var]
            if callable(x):
                return x()
            else:
                return str(x)
        except KeyError:
            if braced:
                return '${%s}' % braced
            else:
                return '$' + unbraced
    return _perlVarSubstituteRe.sub(replacer, text)

def findBinaryInPath(s):
    """Return full path of a binary if it's in PATH, otherwise return None."""
    cmdLine = None
    for dir in os.getenv('PATH').split(':'):
        filename = os.path.join(dir, s)
        if os.path.exists(filename):
            cmdLine = filename
            break
    return cmdLine

def commaAndify(seq, comma=',', And='and'):
    """Given a a sequence, returns an English clause for that sequence.

    I.e., given [1, 2, 3], returns '1, 2, and 3'
    """
    L = list(seq)
    if len(L) == 0:
        return ''
    elif len(L) == 1:
        return ''.join(L) # We need this because it raises TypeError.
    elif len(L) == 2:
        L.insert(1, And)
        return ' '.join(L)
    else:
        L[-1] = '%s %s' % (And, L[-1])
        sep = '%s ' % comma
        return sep.join(L)

_unCommaTheRe = re.compile(r'(.*),\s*(the)$', re.I)
def unCommaThe(s):
    """Takes a string of the form 'foo, the' and turns it into 'the foo'."""
    m = _unCommaTheRe.match(s)
    if m is not None:
        return '%s %s' % (m.group(2), m.group(1))
    else:
        return s

def wrapLines(s):
    """Word wraps several paragraphs in a string s."""
    L = []
    for line in s.splitlines():
        L.append(textwrap.fill(line))
    return '\n'.join(L)

def ellipsisify(s, n):
    """Returns a shortened version of s.  Produces up to the first n chars at
    the nearest word boundary.
    """
    if len(s) <= n:
        return s
    else:
        return (textwrap.wrap(s, n-3)[0] + '...')

plurals = TwoWayDictionary({})
def matchCase(s1, s2):
    """Matches the case of s1 in s2"""
    if s1.isupper():
        return s2.upper()
    else:
        L = list(s2)
        for (i, char) in enumerate(s1[:len(s2)]):
            if char.isupper():
                L[i] = L[i].upper()
        return ''.join(L)

consonants = 'bcdfghjklmnpqrstvwxz'
_pluralizeRegex = re.compile('[%s]y$' % consonants)
def pluralize(s, i=2):
    """Returns the plural of s based on its number i.  Put any exceptions to
    the general English rule of appending 's' in the plurals dictionary.
    """
    if i == 1:
        return s
    else:
        lowered = s.lower()
        # Exception dictionary
        if lowered in plurals:
            return matchCase(s, plurals[lowered])
        # Words ending with 'ch', 'sh' or 'ss' such as 'punch(es)', 'fish(es)
        # and miss(es)
        elif any(lowered.endswith, ['x', 'ch', 'sh', 'ss']):
            return matchCase(s, s+'es')
        # Words ending with a consonant followed by a 'y' such as
        # 'try (tries)' or 'spy (spies)'
        elif _pluralizeRegex.search(lowered):
            return matchCase(s, s[:-1] + 'ies')
        # In all other cases, we simply add an 's' to the base word
        else:
            return matchCase(s, s+'s')

_depluralizeRegex = re.compile('[%s]ies' % consonants)
def depluralize(s):
    """Returns the singular of s."""
    lowered = s.lower()
    if lowered in plurals:
        return matchCase(s, plurals[lowered])
    elif any(lowered.endswith, ['ches', 'shes', 'sses']):
        return s[:-2]
    elif re.search(_depluralizeRegex, lowered):
        return s[:-3] + 'y'
    else:
        if lowered.endswith('s'):
            return s[:-1] # Chop off 's'.
        else:
            return s # Don't know what to do.

def nItems(item, n, between=None):
    """Works like this:

    >>> nItems('clock', 1)
    '1 clock'

    >>> nItems('clock', 10)
    '10 clocks'

    >>> nItems('clock', 10, between='grandfather')
    '10 grandfather clocks'
    """
    if between is None:
        return '%s %s' % (n, pluralize(item, n))
    else:
        return '%s %s %s' % (n, between, pluralize(item, n))

def be(i):
    """Returns the form of the verb 'to be' based on the number i."""
    if i == 1:
        return 'is'
    else:
        return 'are'

def has(i):
    """Returns the form of the verb 'to have' based on the number i."""
    if i == 1:
        return 'has'
    else:
        return 'have'

def sortBy(f, L):
    """Uses the decorate-sort-undecorate pattern to sort L by function f."""
    for (i, elt) in enumerate(L):
        L[i] = (f(elt), i, elt)
    L.sort()
    for (i, elt) in enumerate(L):
        L[i] = L[i][2]

if sys.version_info < (2, 4, 0):
    def sorted(iterable, cmp=None, key=None, reversed=False):
        L = list(iterable)
        if key is not None:
            assert cmp is None, 'Can\'t use both cmp and key.'
            sortBy(key, L)
        else:
            L.sort(cmp)
        if reversed:
            L.reverse()
        return L

    __builtins__['sorted'] = sorted

def mktemp(suffix=''):
    """Gives a decent random string, suitable for a filename."""
    r = random.Random()
    m = md5.md5(suffix)
    r.seed(time.time())
    s = str(r.getstate())
    for x in xrange(0, random.randrange(400), random.randrange(1, 5)):
        m.update(str(x))
        m.update(s)
        m.update(str(time.time()))
        s = m.hexdigest()
    return sha.sha(s + str(time.time())).hexdigest() + suffix

def itersplit(isSeparator, iterable, maxsplit=-1, yieldEmpty=False):
    """itersplit(isSeparator, iterable, maxsplit=-1, yieldEmpty=False)

    Splits an iterator based on a predicate isSeparator."""
    if isinstance(isSeparator, basestring):
        f = lambda s: s == isSeparator
    else:
        f = isSeparator
    acc = []
    for element in iterable:
        if maxsplit == 0 or not f(element):
            acc.append(element)
        else:
            maxsplit -= 1
            if acc or yieldEmpty:
                yield acc
            acc = []
    if acc or yieldEmpty:
        yield acc

def flatten(seq, strings=False):
    """Flattens a list of lists into a single list.  See the test for examples.
    """
    for elt in seq:
        if not strings and type(elt) == str or type(elt) == unicode:
            yield elt
        else:
            try:
                for x in flatten(elt):
                    yield x
            except TypeError:
                yield elt

def saltHash(password, salt=None, hash='sha'):
    if salt is None:
        salt = mktemp()[:8]
    if hash == 'sha':
        hasher = sha.sha
    elif hash == 'md5':
        hasher = md5.md5
    return '|'.join([salt, hasher(salt + password).hexdigest()])

def safeEval(s, namespace={'True': True, 'False': False, 'None': None}):
    """Evaluates s, safely.  Useful for turning strings into tuples/lists/etc.
    without unsafely using eval()."""
    try:
        node = compiler.parse(s)
    except SyntaxError, e:
        raise ValueError, 'Invalid string: %s.' % e
    nodes = compiler.parse(s).node.nodes
    if not nodes:
        if node.__class__ is compiler.ast.Module:
            return node.doc
        else:
            raise ValueError, 'Unsafe string: %s' % quoted(s)
    node = nodes[0]
    if node.__class__ is not compiler.ast.Discard:
        raise ValueError, 'Invalid expression: %s' % quoted(s)
    node = node.getChildNodes()[0]
    def checkNode(node):
        if node.__class__ is compiler.ast.Const:
            return True
        if node.__class__ in (compiler.ast.List,
                              compiler.ast.Tuple,
                              compiler.ast.Dict):
            return all(checkNode, node.getChildNodes())
        if node.__class__ is compiler.ast.Name:
            if node.name in namespace:
                return True
            else:
                return False
        else:
            return False
    if checkNode(node):
        return eval(s, namespace, namespace)
    else:
        raise ValueError, 'Unsafe string: %s' % quoted(s)

def exnToString(e):
    """Turns a simple exception instance into a string (better than str(e))"""
    strE = str(e)
    if strE:
        return '%s: %s' % (e.__class__.__name__, strE)
    else:
        return e.__class__.__name__

class IterableMap(object):
    """Define .iteritems() in a class and subclass this to get the other iters.
    """
    def iteritems(self):
        raise NotImplementedError

    def iterkeys(self):
        for (key, _) in self.iteritems():
            yield key
    __iter__ = iterkeys

    def itervalues(self):
        for (_, value) in self.iteritems():
            yield value

    def items(self):
        return list(self.iteritems())

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def __len__(self):
        ret = 0
        for _ in self.iteritems():
            ret += 1
        return ret

    def __nonzero__(self):
        for _ in self.iteritems():
            return True
        return False


def nonCommentLines(fd):
    for line in fd:
        if not line.startswith('#'):
            yield line

def nonEmptyLines(fd):
##     for line in fd:
##         if line.strip():
##             yield line
    return ifilter(str.strip, fd)

def nonCommentNonEmptyLines(fd):
    return nonEmptyLines(nonCommentLines(fd))

def changeFunctionName(f, name, doc=None):
    if doc is None:
        doc = f.__doc__
    newf = types.FunctionType(f.func_code, f.func_globals, name,
                              f.func_defaults, f.func_closure)
    newf.__doc__ = doc
    return newf

def getSocket(host):
    """Returns a socket of the correct AF_INET type (v4 or v6) in order to
    communicate with host.
    """
    host = socket.gethostbyname(host)
    if isIP(host):
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    elif isIPV6(host):
        return socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    else:
        raise socket.error, 'Something wonky happened.'

def isIP(s):
    """Returns whether or not a given string is an IPV4 address.

    >>> isIP('255.255.255.255')
    1

    >>> isIP('abc.abc.abc.abc')
    0
    """
    try:
        return bool(socket.inet_aton(s))
    except socket.error:
        return False

def bruteIsIPV6(s):
    if s.count('::') <= 1:
        L = s.split(':')
        if len(L) <= 8:
            for x in L:
                if x:
                    try:
                        int(x, 16)
                    except ValueError:
                        return False
            return True
    return False

def isIPV6(s):
    """Returns whether or not a given string is an IPV6 address."""
    try:
        if hasattr(socket, 'inet_pton'):
            return bool(socket.inet_pton(socket.AF_INET6, s))
        else:
            return bruteIsIPV6(s)
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET6, '::')
        except socket.error:
            # We gotta fake it.
            return bruteIsIPV6(s)
        return False

class InsensitivePreservingDict(UserDict.DictMixin, object):
    def key(self, s):
        """Override this if you wish."""
        if s is not None:
            s = s.lower()
        return s

    def __init__(self, dict=None, key=None):
        if key is not None:
            self.key = key
        self.data = {}
        if dict is not None:
            self.update(dict)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           super(InsensitivePreservingDict, self).__repr__())

    def fromkeys(cls, keys, s=None, dict=None, key=None):
        d = cls(dict=dict, key=key)
        for key in keys:
            d[key] = s
        return d
    fromkeys = classmethod(fromkeys)

    def __getitem__(self, k):
        return self.data[self.key(k)][1]

    def __setitem__(self, k, v):
        self.data[self.key(k)] = (k, v)

    def __delitem__(self, k):
        del self.data[self.key(k)]

    def iteritems(self):
        return self.data.itervalues()

    def keys(self):
        L = []
        for (k, _) in self.iteritems():
            L.append(k)
        return L

    def __reduce__(self):
        return (self.__class__, (dict(self.data.values()),))


class NormalizingSet(sets.Set):
    def __init__(self, iterable=()):
        iterable = itertools.imap(self.normalize, iterable)
        super(NormalizingSet, self).__init__(iterable)

    def normalize(self, x):
        return x

    def add(self, x):
        return super(NormalizingSet, self).add(self.normalize(x))

    def remove(self, x):
        return super(NormalizingSet, self).remove(self.normalize(x))

    def discard(self, x):
        return super(NormalizingSet, self).discard(self.normalize(x))

    def __contains__(self, x):
        return super(NormalizingSet, self).__contains__(self.normalize(x))
    has_key = __contains__

def mungeEmailForWeb(s):
    s = s.replace('@', ' AT ')
    s = s.replace('.', ' DOT ')
    return s

class AtomicFile(file):
    """Used for files that need to be atomically written -- i.e., if there's a
    failure, the original file remains, unmodified.  mode must be 'w' or 'wb'"""
    def __init__(self, filename, mode='w', allowEmptyOverwrite=True,
                 makeBackupIfSmaller=True, tmpDir=None, backupDir=None):
        if mode not in ('w', 'wb'):
            raise ValueError, 'Invalid mode: %s' % quoted(mode)
        self.rolledback = False
        self.allowEmptyOverwrite = allowEmptyOverwrite
        self.makeBackupIfSmaller = makeBackupIfSmaller
        self.filename = filename
        self.backupDir = backupDir
        if tmpDir is None:
            # If not given a tmpDir, we'll just put a random token on the end
            # of our filename and put it in the same directory.
            self.tempFilename = '%s.%s' % (self.filename, mktemp())
        else:
            # If given a tmpDir, we'll get the basename (just the filename, no
            # directory), put our random token on the end, and put it in tmpDir
            tempFilename = '%s.%s' % (os.path.basename(self.filename), mktemp())
            self.tempFilename = os.path.join(tmpDir, tempFilename)
        # This doesn't work because of the uncollectable garbage effect.
        # self.__parent = super(AtomicFile, self)
        super(AtomicFile, self).__init__(self.tempFilename, mode)

    def rollback(self):
        if not self.closed:
            super(AtomicFile, self).close()
            if os.path.exists(self.tempFilename):
                os.remove(self.tempFilename)
            self.rolledback = True

    def close(self):
        if not self.rolledback:
            super(AtomicFile, self).close()
            # We don't mind writing an empty file if the file we're overwriting
            # doesn't exist.
            newSize = os.path.getsize(self.tempFilename)
            originalExists = os.path.exists(self.filename)
            if newSize or self.allowEmptyOverwrite or not originalExists:
                if originalExists:
                    oldSize = os.path.getsize(self.filename)
                    if self.makeBackupIfSmaller and newSize < oldSize:
                        now = int(time.time())
                        backupFilename = '%s.backup.%s' % (self.filename, now)
                        if self.backupDir is not None:
                            backupFilename = os.path.basename(backupFilename)
                            backupFilename = os.path.join(self.backupDir,
                                                          backupFilename)
                        shutil.copy(self.filename, backupFilename)
                # We use shutil.move here instead of os.rename because
                # the latter doesn't work on Windows when self.filename
                # (the target) already exists.  shutil.move handles those
                # intricacies for us.

                # This raises IOError if we can't write to the file.  Since
                # in *nix, it only takes write perms to the *directory* to
                # rename a file (and shutil.move will use os.rename if
                # possible), we first check if we have the write permission
                # and only then do we write.
                fd = file(self.filename, 'a')
                fd.close()
                shutil.move(self.tempFilename, self.filename)
                
        else:
            raise ValueError, 'AtomicFile.close called after rollback.'

    def __del__(self):
        # We rollback because if we're deleted without being explicitly closed,
        # that's bad.  We really should log this here, but as of yet we've got
        # no logging facility in utils.  I've got some ideas for this, though.
        self.rollback()

def transactionalFile(*args, **kwargs):
    # This exists so it can be replaced by a function that provides the tmpDir.
    # We do that replacement in conf.py.
    return AtomicFile(*args, **kwargs)

def stackTrace(frame=None, compact=True):
    if frame is None:
        frame = sys._getframe()
    if compact:
        L = []
        while frame:
            lineno = frame.f_lineno
            funcname = frame.f_code.co_name
            filename = os.path.basename(frame.f_code.co_filename)
            L.append('[%s|%s|%s]' % (filename, funcname, lineno))
            frame = frame.f_back
        return textwrap.fill(' '.join(L))
    else:
        return traceback.format_stack(frame)

def callTracer(fd=None, basename=True):
    if fd is None:
        fd = sys.stdout
    def tracer(frame, event, _):
        if event == 'call':
            code = frame.f_code
            lineno = frame.f_lineno
            funcname = code.co_name
            filename = code.co_filename
            if basename:
                filename = os.path.basename(filename)
            print >>fd, '%s: %s(%s)' % (filename, funcname, lineno)
    return tracer


def toBool(s):
    s = s.strip().lower()
    if s in ('true', 'on', 'enable', 'enabled', '1'):
        return True
    elif s in ('false', 'off', 'disable', 'disabled', '0'):
        return False
    else:
        raise ValueError, 'Invalid string for toBool: %s' % quoted(s)

def mapinto(f, L):
    for (i, x) in enumerate(L):
        L[i] = f(x)

if __name__ == '__main__':
    import doctest
    doctest.testmod(sys.modules['__main__'])


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
