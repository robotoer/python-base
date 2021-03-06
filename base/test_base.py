#!/usr/bin/env python3
# -*- mode: python -*-
# -*- coding: utf-8 -*-

"""Tests for module base.base"""

import logging
import os
import sys
import unittest

from base import base


class TestBase(unittest.TestCase):

  def testTouch(self):
    path = base.RandomAlphaNumWord(16)
    try:
      self.assertFalse(os.path.exists(path))
      base.Touch(path)
      self.assertTrue(os.path.exists(path))
      base.Touch(path)
      self.assertTrue(os.path.exists(path))
    finally:
      os.remove(path)

  def testUnCamelCase(self):
    self.assertEqual('jira', base.UnCamelCase('JIRA'))
    self.assertEqual('jira_tool', base.UnCamelCase('JIRATool'))
    self.assertEqual('jira_tool', base.UnCamelCase('jira_tool'))
    self.assertEqual('jira_tool', base.UnCamelCase('jira tool'))
    self.assertEqual('jira_tool', base.UnCamelCase('Jira tool'))
    self.assertEqual('jira_tool', base.UnCamelCase(' Jira tool'))
    self.assertEqual('status_csv', base.UnCamelCase(' StatusCSV'))


def Main(args):
  args = list(args)
  args.insert(0, sys.argv[0])
  unittest.main(argv=args)


if __name__ == '__main__':
  base.Run(Main)
