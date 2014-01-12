#!/usr/bin/env python3
# -*- mode: python -*-
# -*- coding: utf-8 -*-

"""Unit-tests for Workflow and Task."""

import http.client
import logging
import os
import re
import sys
import unittest

from base import base
from workflow import workflow


class SuccessTask(workflow.Task):
  def Run(self):
    return self.SUCCESS


class FailureTask(workflow.Task):
  def Run(self):
    return self.FAILURE


class TestWorkflow(unittest.TestCase):
  def testEmptyWorkflow(self):
    flow = workflow.Workflow()
    flow.Build()
    flow.Process()

  def testLinearWorkflowSuccess(self):
    flow = workflow.Workflow()
    task1 = SuccessTask(workflow=flow, task_id='task1')
    task2 = SuccessTask(workflow=flow, task_id='task2', runs_after=[task1])
    task3 = SuccessTask(workflow=flow, task_id='task3', runs_after=[task2])
    task4 = SuccessTask(workflow=flow, task_id='task4', runs_after=[task3])
    task5 = SuccessTask(workflow=flow, task_id='task5', runs_after=[task4])
    flow.Build()
    flow.Process(nworkers=10)
    self.assertEqual(workflow.TaskState.SUCCESS, task1.state)
    self.assertEqual(workflow.TaskState.SUCCESS, task2.state)
    self.assertEqual(workflow.TaskState.SUCCESS, task3.state)
    self.assertEqual(workflow.TaskState.SUCCESS, task4.state)
    self.assertEqual(workflow.TaskState.SUCCESS, task5.state)

    print(flow.DumpAsDot())

  def testParallelWorkflowSuccess(self):
    flow = workflow.Workflow()
    task1 = SuccessTask(workflow=flow, task_id='task1')
    task2 = SuccessTask(workflow=flow, task_id='task2')
    task3 = SuccessTask(workflow=flow, task_id='task3')
    task4 = SuccessTask(workflow=flow, task_id='task4')
    task5 = SuccessTask(workflow=flow, task_id='task5')
    flow.Build()
    flow.Process(nworkers=10)
    self.assertEqual(workflow.TaskState.SUCCESS, task1.state)
    self.assertEqual(workflow.TaskState.SUCCESS, task2.state)
    self.assertEqual(workflow.TaskState.SUCCESS, task3.state)
    self.assertEqual(workflow.TaskState.SUCCESS, task4.state)
    self.assertEqual(workflow.TaskState.SUCCESS, task5.state)

  def testLinearWorkflowFailure(self):
    flow = workflow.Workflow()
    task1 = SuccessTask(workflow=flow, task_id='task1')
    task2 = FailureTask(workflow=flow, task_id='task2', runs_after=[task1])
    task3 = SuccessTask(workflow=flow, task_id='task3', runs_after=[task2])
    task4 = SuccessTask(workflow=flow, task_id='task4', runs_after=[task3])
    task5 = SuccessTask(workflow=flow, task_id='task5', runs_after=[task4])
    flow.Build()
    flow.Process(nworkers=10)
    self.assertEqual(workflow.TaskState.SUCCESS, task1.state)
    self.assertEqual(workflow.TaskState.FAILURE, task2.state)
    self.assertEqual(workflow.TaskState.FAILURE, task3.state)
    self.assertEqual(workflow.TaskState.FAILURE, task4.state)
    self.assertEqual(workflow.TaskState.FAILURE, task5.state)

  def testWorkflowFailure(self):
    flow = workflow.Workflow()
    task1 = SuccessTask(workflow=flow, task_id='task1')
    task2 = FailureTask(workflow=flow, task_id='task2', runs_after=[task1])
    task3 = SuccessTask(workflow=flow, task_id='task3', runs_after=[task2])
    task4 = SuccessTask(workflow=flow, task_id='task4', runs_after=[task2, task3])
    flow.Build()
    flow.Process(nworkers=10)
    self.assertEqual(workflow.TaskState.SUCCESS, task1.state)
    self.assertEqual(workflow.TaskState.FAILURE, task2.state)
    self.assertEqual(workflow.TaskState.FAILURE, task3.state)
    self.assertEqual(workflow.TaskState.FAILURE, task4.state)

  def testCircularDep(self):
    flow = workflow.Workflow()
    task1 = SuccessTask(workflow=flow, task_id='task1', runs_after=['task3'])
    task2 = FailureTask(workflow=flow, task_id='task2', runs_after=[task1])
    task3 = SuccessTask(workflow=flow, task_id='task3', runs_after=[task2])
    try:
      flow.Build()
      self.fail()
    except workflow.CircularDependencyError:
      pass

  def testCircularDep2(self):
    flow = workflow.Workflow()
    task1 = SuccessTask(workflow=flow, task_id='task1')
    task2 = FailureTask(workflow=flow, task_id='task2')
    task3 = SuccessTask(workflow=flow, task_id='task3')
    task2.RunsAfter(task3)
    task2.RunsBefore(task3)
    try:
      flow.Build()
      self.fail()
    except workflow.CircularDependencyError:
      pass

  def testPersistentTaskRunNoFile(self):
    """Persistent task runs if output file does not exist.

    No output file is created if task fails.
    """
    class PTask(workflow.LocalFSPersistentTask):
      def Run(self):
        return self.FAILURE

    flow = workflow.Workflow()
    file_path = base.RandomAlphaNumWord(16)
    task = PTask(
        output_file_path=file_path,
        task_id='task',
        workflow=flow,
    )
    flow.Build()
    self.assertFalse(os.path.exists(file_path))
    self.assertFalse(flow.Process())
    self.assertFalse(os.path.exists(file_path))

  def testPersistentTaskNoRunIfFile(self):
    """Persistent task does not run if output file already exists."""
    class PTask(workflow.LocalFSPersistentTask):
      def Run(self):
        return self.FAILURE

    flow = workflow.Workflow()
    file_path = base.RandomAlphaNumWord(16)
    base.Touch(file_path)
    try:
      task = PTask(
          output_file_path=file_path,
          task_id='task',
          workflow=flow,
      )
      flow.Build()
      self.assertTrue(os.path.exists(file_path))
      self.assertTrue(flow.Process())
      self.assertTrue(os.path.exists(file_path))
    finally:
      base.Remove(file_path)

  def testPersistentTaskRunCreateFile(self):
    """Running a persistent task with success creates the output file."""
    class PTask(workflow.LocalFSPersistentTask):
      def Run(self):
        return self.SUCCESS

    flow = workflow.Workflow()
    file_path = base.RandomAlphaNumWord(16)
    try:
      task = PTask(
          output_file_path=file_path,
          task_id='task',
          workflow=flow,
      )
      flow.Build()
      self.assertFalse(os.path.exists(file_path))
      self.assertTrue(flow.Process())
      self.assertTrue(os.path.exists(file_path))
    finally:
      base.Remove(file_path)

  def testDumpAsSVG(self):
    flow1 = workflow.Workflow()
    task1 = SuccessTask(workflow=flow1, task_id='task1')
    task2 = FailureTask(workflow=flow1, task_id='task2')
    task3 = SuccessTask(workflow=flow1, task_id='task3')
    task2.RunsAfter(task1)
    task3.RunsAfter(task2)
    flow1.Build()

    svg_source = flow1.DumpAsSVG()
    logging.debug('SVG source:\n%s', svg_source)

    server = workflow.WorkflowHTTPMonitor(interface='127.0.0.1', port=0)
    server.Start()
    try:
      flow1.Process()

      conn = http.client.HTTPConnection(
          host='127.0.0.1',
          port=server.server_port,
      )
      conn.connect()
      try:
        conn.request(method='GET', url='')
        response = conn.getresponse()
        self.assertEqual(404, response.getcode())

        server.SetWorkflow(flow1)

        conn.request(method='GET', url='')
        response = conn.getresponse()
        self.assertEqual(200, response.getcode())
        self.assertEqual('image/svg+xml', response.getheader('Content-Type'))
        logging.debug('HTTP response: %r', response.read())
      finally:
        conn.close()

    finally:
      server.Stop()

  def disabledTestWorkflowDiff(self):
    flow1 = workflow.Workflow()
    task1 = SuccessTask(workflow=flow1, task_id='task1')
    task2 = SuccessTask(workflow=flow1, task_id='task2')
    task3 = SuccessTask(workflow=flow1, task_id='task3')
    task2.RunsAfter(task1)
    task3.RunsAfter(task2)
    flow1.Build()

    flow2 = workflow.Workflow()
    task1 = SuccessTask(workflow=flow2, task_id='task1')
    task2b = SuccessTask(workflow=flow2, task_id='task2b')
    task3 = SuccessTask(workflow=flow2, task_id='task3')
    task2b.RunsAfter(task1)
    task3.RunsAfter(task2b)
    task3.RunsAfter(task1)
    flow2.Build()

    workflow.DiffWorkflow(flow1, flow2)


# ------------------------------------------------------------------------------


def Main(args):
  args = list(args)
  args.insert(0, sys.argv[0])
  unittest.main(argv=args)


if __name__ == '__main__':
  base.Run(Main)
