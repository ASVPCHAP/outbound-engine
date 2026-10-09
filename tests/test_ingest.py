import os
import tempfile
import unittest

from engine.ingest import build, contact_key, icp_keywords, icp_match, parse

ICP = {"buyer_titles": "Founder/CEO; VP Sales; Head of Growth; Head of BD"}
KW = icp_keywords(ICP)

# Made-up rows in LinkedIn's export layout, preamble included.
CONNECTIONS = """Notes:
"When exporting your connection data, you may notice that some of the email addresses are missing."

First Name,Last Name,URL,Email Address,Company,Position,Connected On
Jane,Doe,https://www.linkedin.com/in/jane-doe-test,,Acme SaaS,Co-Founder & CEO,01 Oct 2026
Bob,Roe,https://www.linkedin.com/in/bob-roe-test,bob@example.com,Acme SaaS,"VP, Sales",02 Oct 2026
Cal,Poe,https://www.linkedin.com/in/cal-poe-test,,Other Co,Software Engineer,03 Oct 2026
Jane,Doe,https://www.linkedin.com/in/jane-doe-test/,,Acme SaaS,Co-Founder & CEO,01 Oct 2026
"""


def write_tmp(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


class Ingest(unittest.TestCase):
    def test_icp_match(self):
        self.assertEqual(icp_match("Co-Founder & CEO", KW), "founder, ceo")
        self.assertEqual(icp_match("VP, Sales", KW), "vp sales")
        self.assertEqual(icp_match("SVP of Sales", KW), "vp sales")
        self.assertEqual(icp_match("Head of Business Development", KW), "head bd")
        self.assertEqual(icp_match("Software Engineer", KW), "")

    def test_contact_key_is_stable(self):
        a = contact_key({"linkedin_url": "https://www.linkedin.com/in/Jane-Doe/"})
        b = contact_key({"linkedin_url": "https://linkedin.com/in/jane-doe?trk=x"})
        self.assertEqual(a, b)
        self.assertEqual(contact_key({"email": " Bob@Example.com"}), "email:bob@example.com")

    def test_connections_import(self):
        path = write_tmp(CONNECTIONS)
        try:
            rows = list(parse(path))
        finally:
            os.unlink(path)
        self.assertEqual(len(rows), 4)  # preamble skipped
        accounts, contacts = build(rows, "t", "network", KW, only_icp=True)
        self.assertEqual(sorted(c["full_name"] for c in contacts), ["Bob Roe", "Jane Doe"])
        self.assertEqual(len(accounts), 1)  # one company, de-duplicated
        self.assertTrue(all(c["ring"] == "network" for c in contacts))
        _, everyone = build(rows, "t", "network", KW, only_icp=False)
        self.assertEqual(len(everyone), 3)  # duplicate Jane merged

    def test_past_customers_generic_csv(self):
        path = write_tmp("Full Name,Email,Company,Title,Website\n"
                         "Dee Lee,dee@example.org,Lee Builders,Owner,leebuilders.example\n")
        try:
            _, contacts = build(parse(path), "t", "past_customer", KW, only_icp=False)
        finally:
            os.unlink(path)
        self.assertEqual(contacts[0]["contact_id"], "t:email:dee@example.org")
        self.assertEqual(contacts[0]["_account"], "t:leebuilders-example")


if __name__ == "__main__":
    unittest.main()
