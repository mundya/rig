import sys
from mock import Mock as MagicMock
class Mock(MagicMock):
 @classmethod
 def __getattr__(cls,name):return Mock()
MOCK_MODULES=['pygtk','gtk','gobject','argparse','numpy','pandas']
sys.modules.update((mod_name,Mock()) for mod_name in MOCK_MODULES)
AUTHORS='Project Rig'
import sys
import os
sys.path.insert(0,os.path.abspath('../..'))
extensions=['sphinx.ext.autodoc','sphinx.ext.autosummary','sphinx.ext.intersphinx','sphinx.ext.doctest','numpydoc']
numpydoc_show_class_members=False
templates_path=['_templates']
source_suffix='.rst'
master_doc='index'
project='Rig'
copyright='2015, the Rig Project'
autodoc_member_order='bysource'
version='0.1'
release='0.1'
exclude_patterns=[]
pygments_style='sphinx'
intersphinx_mapping={'python':('http://docs.python.org/3',None)}
html_theme='nature'
html_static_path=['_static']
htmlhelp_basename='Rigdoc'
latex_elements={}
latex_documents=[('index','Rig.tex','Rig Documentation',AUTHORS,'manual')]
man_pages=[('index','rig','Rig Documentation',[AUTHORS],1)]
texinfo_documents=[('index','Rig','Rig Documentation',AUTHORS,'Rig','Tools for mapping problems to SpiNNaker','Miscellaneous')]
