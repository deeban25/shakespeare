"""
Concordance (and statistics) for texts in database.

To build concordance use ConcordanceBuilder.  To access concordance/statistics
use Concordance/Statistics class.  Concordance and statistics are provided as
dictionaries keyed by words.

NB: all word keys have been lower-cased in order to render them
case-insensitive
"""
import re

import sqlobject

import milton.index
import milton.cache


class ConcordanceBase(object):
    """
    TODO: caching??
    """
    sqlcc = milton.model.Concordance
    sqlstat = milton.model.Statistic

    def __init__(self, filter_names=None):
        """
        @param filter_names: a list of id names with which to filter results
            (i.e. only return results relating to those texts)
        """
        self._filter_names = filter_names
        self.sqlcc_filter = self._make_filter(self.sqlcc)
        self.sqlstat_filter = self._make_filter(self.sqlstat)

    def _make_filter(self, sqlobj):
        sql_filter = True
        if self._filter_names is not None:
            arglist = []
            for name in self._filter_names:
                newarg = sqlobj.q.textID == self._name2id(name)
                arglist.append(newarg)
            sql_filter = sqlobject.OR(*arglist)
        return sql_filter
    
    def _name2id(self, name):
        return milton.model.Material.byName(name).id

    def keys(self):
        """Return list of *distinct* words in concordance/statistics
        """
        all = self.sqlstat.select(self.sqlstat_filter,
                           orderBy=self.sqlstat.q.word,
                           )
        words = [ xx.word for xx in list(all) ]
        distinct = list(set(words))
        distinct.sort()
        return distinct


class Concordance(ConcordanceBase):
    """Concordance by word for a set of texts
    """

    def get(self, word):
        """Get list of occurrences for word
        @return: sqlobject query list 
        """
        select = self.sqlcc.select(sqlobject.AND(self.sqlcc_filter, self.sqlcc.q.word==word))
        return select

class Statistics(ConcordanceBase):

    def get(self, word):
        select = self.sqlstat.select(
            sqlobject.AND(self.sqlstat_filter, self.sqlstat.q.word==word)
            )
        total = 0
        for stat in select:
            total += stat.occurrences
        return total

class ConcordanceBuilder(object):
    """Build a concordance and associated statistics for a set of texts.
    
    """

    # multiline, unicode and ignorecase
    word_regex = re.compile(r'\b(\w+)\b', re.U | re.M | re.I)

    words_to_ignore = [ 
        # 'a', 'the', 'and', 'as', 'are', 'be', 'but', 'in'
                        ]
    non_words = [ 
            'd', # accus'd
            't',
            ]

    def is_roman_numeral(self, word):
        digits = [ 'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix' ]
        others = [ 'l', 'x', 'c' ]
        if word == 'i': return False # exception because this conflicts with I
        while word[0] in others:
            if len(word) == 1:
                return True
            else:
                word = word[1:]
        return word in digits

    def ignore_word(self, word):
        "Return True if this word should not be added to the concordance."
        bool1 = word in self.words_to_ignore
        bool2 = word in self.non_words
        # do roman numerals
        bool3 = self.is_roman_numeral(word)
        return bool1 or bool2 or bool3

    def _text_already_done(self, text):
        numrecs = milton.model.Concordance.select(
                milton.model.Concordance.q.textID==text.id
                ).count()
        return numrecs > 0

    def add_text(self, name, text=None):
        """Add a text to the concordance.
        @param name: name of text to add
        @param text: [optional] a file-like object containing text data. If not
            provided will default to using file in cache associated with named
            text
        """
        dmText = milton.model.Material.byName(name)
        if self._text_already_done(dmText):
            msg = 'Have already added to concordance text: %s' % dmText
            # raise ValueError(msg)
            print msg
            print 'Skipping'
            return
        if text is None:
            tpath = dmText.get_cache_path('plain')
            text = file(tpath)
        lineCount = 0
        charIndex = 0
        stats = {}
        trans = milton.model.Concordance._connection.transaction()
        for line in text.readlines():
            for match in self.word_regex.finditer(line):
                word = match.group().lower() # case insensitive
                if self.ignore_word(word):
                    continue
                milton.model.Concordance(connection=trans,
                                           text=dmText,
                                           word=word,
                                           line=lineCount,
                                           char_index=charIndex+match.start())
                stats[word] = stats.get(word, 0) + 1
            lineCount += 1
            charIndex += len(line)
        trans.commit()
        trans = milton.model.Concordance._connection.transaction()
        for word, value in stats.items():
            tresults  = milton.model.Statistic.select(
                sqlobject.AND(
                    milton.model.Statistic.q.textID == dmText.id,
                    milton.model.Statistic.q.word == word
                    ))
            try:
                dbstat = list(tresults)[0]
                dbstat.occurrences += value
            except:
                milton.model.Statistic(
                        connection=trans,
                        text=dmText,
                        word=word,
                        occurrences=value
                        )
        trans.commit()


    def remove_text(self, name):
        """Remove a text from the concordance.

        @param name: as for add_text
        """
        dmText = milton.model.Material.byName(name)
        recs = milton.model.Concordance.select(
                milton.model.Concordance.q.textID==dmText.id
                )
        for rec in recs:
            milton.model.Concordance.delete(rec.id)
        stats = milton.model.Statistic.select(
                milton.model.Statistic.q.textID==dmText.id
                )
        for stat in stats:
            milton.model.Statistic.delete(stat.id)

