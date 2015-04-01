import pytest
import _pytest
from collections import defaultdict
from toposort import toposort
@pytest.fixture(scope='session')
def spinnaker_ip(request):return request.config.getoption('spinnaker',skip=True)[0]
@pytest.fixture(scope='session')
def bmp_ip(request):return request.config.getoption('bmp',skip=True)[0]
@pytest.fixture(scope='session')
def spinnaker_width(request):return int(request.config.getoption('spinnaker',skip=True)[1])
@pytest.fixture(scope='session')
def spinnaker_height(request):return int(request.config.getoption('spinnaker',skip=True)[2])
@pytest.fixture(scope='session')
def is_spinn_5_board(request,spinnaker_width,spinnaker_height):
 spinn_5=bool(request.config.getoption('spinn5'))
 if not spinn_5:pytest.skip()
 else:assert spinnaker_width==8;assert spinnaker_height==8;return spinn_5
def pytest_addoption(parser):parser.addoption('--no-boot',action='store_false',help='Skip booting/power-cycling the board during tests.');parser.addoption('--spinnaker',nargs=3,help='Run tests on a SpiNNaker machine. Specify the IP address or hostname of the SpiNNaker machine to use and the width and the height of the machine.');parser.addoption('--spinn5',action='store_true',default=False,help='The SpiNNaker machine is a single SpiNN-5 board.');parser.addoption('--bmp',nargs=1,help="Run tests against a real SpiNNaker board's BMP. Specify the IP address or hostname of the BMP to use.")
def pytest_runtest_makereport(item,call):
 if 'incremental' in item.keywords:
  if call.excinfo is not None:
   if call.excinfo.type is not _pytest.runner.Skipped and call.excinfo.type is not _pytest.skipping.XFailed:parent=item.parent;parent._previousfailed=item
def pytest_runtest_setup(item):
 if 'incremental' in item.keywords:
  previousfailed=getattr(item.parent,'_previousfailed',None)
  if previousfailed is not None:pytest.xfail('previous test failed (%s)'%previousfailed.name)
 for mark,option,message in [('no_boot','--no-boot',"don't (re)boot the SpiNNaker machine")]:
  if getattr(item.obj,mark,None) and not item.config.getoption(option):pytest.skip(message)
def pytest_collection_modifyitems(session,config,items):
 "Adds markers which constrain the ordering of tests.\n\n    Three new markers are defined:\n\n    pytest.mark.order_before(id, ...)\n        Ensure this test is run before any tests with any of the supplied\n        labels.\n    pytest.mark.order_after(id, ...)\n        Ensure this test is run after any tests with any of the supplied\n        labels.\n    pytest.mark.order_id(id, ...)\n        Label the test with the given set of IDs.\n\n    A warning is printed if there is a dependency on an ID which hasn't been\n    defined.\n\n    This method will raise an exception if a cyclic dependency is detected.\n    ";ids=defaultdict(set)
 for item in items:
  if 'order_id' in item.keywords:
   for item_id in item.keywords['order_id'].args:ids[item_id].add(item)
 dependencies=defaultdict(set)
 for item in items:
  if 'order_before' in item.keywords:
   for other_id in item.keywords['order_before'].args:
    if other_id not in ids:print('WARNING: Dependency on ID with no cases {}.'.format(other_id))
    for other_item in ids[other_id]:dependencies[other_item].add(item)
  if 'order_after' in item.keywords:
   for other_id in item.keywords['order_after'].args:
    if other_id not in ids:print('WARNING: Dependency on ID with no cases {}.'.format(other_id))
    for other_item in ids[other_id]:dependencies[item].add(other_item)
 sort_key_lookup={}
 for layer,layer_items in enumerate(toposort(dependencies)):
  for item in layer_items:sort_key_lookup[item]=layer
 cur_key=-1
 for item in items:
  if item in sort_key_lookup:cur_key=sort_key_lookup[item]
  else:sort_key_lookup[item]=cur_key
 items.sort(key=lambda x:sort_key_lookup[x])
