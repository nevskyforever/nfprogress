"""Qt-free canonical user-agreement content shared by every frontend."""

from __future__ import annotations

from hashlib import sha256

from translations_catalog import AGREEMENT_SOURCE


ENGLISH_AGREEMENT_HTML = """
<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body { color: #ffffff; font-family: Arial; font-size: 13pt; }
h1 { font-size: xx-large; } h2 { font-size: x-large; }
p, li { white-space: pre-wrap; }
</style></head><body>
<h1>ADDITIONAL TERMS OF USE FOR NFPROGRESS</h1>
<p>Samara<br>23 July 2026</p>
<h2>1. General Provisions</h2>
<p>1.1. The nfprogress computer program is distributed under the GNU General
Public License version 3 (GPLv3).</p>
<p>1.2. This document neither modifies nor restricts the rights granted to the
User under GPLv3. It governs only matters not covered by that license.</p>
<p>1.3. If this document conflicts with GPLv3, the GPLv3 terms prevail.</p>
<h2>2. Intellectual Property</h2>
<p>2.1. The exclusive rights to the program belong to Roman Ruslanovich
Kishochkin.</p>
<p>2.2. The program is distributed under GPLv3, including the User's right to:</p>
<ul>
<li>use the program;</li>
<li>study how it works;</li>
<li>modify the source code;</li>
<li>distribute original and modified versions of the program in compliance
with GPLv3.</li>
</ul>
<h2>3. Personal Data</h2>
<p>3.1. The program does not require user registration and does not collect
names, email addresses, or other identifying information.</p>
<p>3.2. While the program is running, technical information required for
update checks and error diagnostics may be transmitted automatically,
including:</p>
<ul>
<li>the program version;</li>
<li>the operating system version;</li>
<li>information about errors that occurred.</li>
</ul>
<p>3.3. This information is used solely to ensure that the program functions
correctly and is not used to identify the User.</p>
<h2>4. Disclaimer of Warranties</h2>
<p>4.1. The program is provided “AS IS”.</p>
<p>4.2. To the maximum extent permitted by applicable law, the Copyright
Holder makes no warranties regarding the program, including warranties of
fitness for a particular purpose, uninterrupted operation, or freedom from
errors.</p>
<p>4.3. The User independently decides whether to use the program and assumes
all associated risks.</p>
<h2>5. Limitation of Liability</h2>
<p>5.1. To the extent permitted by the laws of the Russian Federation, the
Copyright Holder shall not be liable for any losses arising from the use of,
or inability to use, the program.</p>
<p>5.2. This clause does not apply where liability cannot be limited by law.</p>
<h2>6. Governing Law</h2>
<p>6.1. Matters not governed by GPLv3 are governed by the laws of the Russian
Federation.</p>
<p>6.2. Before applying to a court, the parties shall seek to resolve any
dispute through negotiation.</p>
<h2>7. Contact Details</h2>
<p>Copyright Holder:<br>Roman Ruslanovich Kishochkin</p>
<p>Email: <b>app@nfpr.ru</b></p>
</body></html>
"""


AGREEMENT_ID = sha256(AGREEMENT_SOURCE.encode('utf-8')).hexdigest()[:16]


def agreement_html(language: str) -> str:
    """Return the same language policy used by the legacy agreement dialog."""
    return AGREEMENT_SOURCE if language == 'ru' else ENGLISH_AGREEMENT_HTML


__all__ = [
    'AGREEMENT_ID', 'ENGLISH_AGREEMENT_HTML', 'agreement_html',
]
