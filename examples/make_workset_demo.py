# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Create fictional inputs and a private local selection for the workset command."""
import hashlib
import json
from pathlib import Path
import sys
from make_wcs_demo import make_demo


if __name__=='__main__':
    root=Path(sys.argv[1]).resolve()
    root.mkdir(parents=True,exist_ok=False)
    make_demo(root/'inputs')
    files=[]
    for name in ['frame-01.fit','frame-03.fit','frame-05.fit']:
        path=root/'inputs'/name
        files.append({'source':str(path),'expected_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (root/'selection.json').write_text(json.dumps({'selection_schema_version':'1.0','files':files},indent=2),encoding='utf-8')
