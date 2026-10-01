Curriculum Workflow
===================

This guide and the curriculum project serve different roles.

``program_guide``
  Shows the current approved structure as published in UVic's calendar.

Curriculum site
  Tracks draft revisions, consultation work, proposal status, and historical context.

The cleanest way to integrate the two is to treat this guide as the official-current baseline and the curriculum site as the proposal workbench. In practice, that means:

1. Start here when you need the currently approved prerequisite or program structure.
2. Use the curriculum board and proposal decks when you need to understand what may change next.
3. Refresh this guide only after the official calendar changes, not when proposals are still in discussion.

Data Sync
---------

The repository now includes a reproducible pull from UVic's public undergraduate calendar endpoints:

.. code-block:: bash

   python scripts/sync_uvic_catalog.py

The sync writes:

* refreshed ``data/eos_program_list.csv`` and ``data/eos_course_list.csv``
* raw program JSON in ``data/catalog/program_details/``
* raw course JSON in ``data/catalog/course_details/``
* summary manifests in ``data/catalog/``

Current scope
-------------

The sync currently captures:

* all programs whose official description names the School of Earth and Ocean Sciences
* all EOS subject courses in the current undergraduate catalog
* all supporting course codes referenced by those SEOS programs and EOS course rules

That makes the pulled data a solid baseline for expanding graph coverage across the full SEOS portfolio, including combined and honours variants that were missing from the earlier hand-built lists.

Program graph validation
------------------------

Run the offline regression suite before rebuilding or publishing:

.. code-block:: bash

   python -m unittest discover -s tests -v
   python scripts/build_static_site.py
   python scripts/verify_static_site.py

Program maps scope course groups to the requirements of that program and stream.
Courses with a shared introductory role or a calendar credit exclusion are not
automatically interchangeable degree requirements. Named courses share a node
only when the published rules list them in the same direct one-course choice
at every occurrence. Related prerequisite courses remain separate from named
requirements. The SVG, course links, colours, and analytics use the same scoped
groups. This preserves, for example, Climate Science's required BIOL 184 while
showing BIOL 186 only as a related prerequisite.
