"""Controlled taxonomy + deterministic tagging for tracker.energy documents.

Two facets:
  doc_type  - what the document IS (protest, order, application, ...)
  topic     - what the document is ABOUT (large-load, interconnection, ...)

Rules are keyword/regex patterns over title + source class. Every applied tag
records the rule that fired (document_tags.rule) so tagging is auditable and
reversible. Accuracy over recall: a rule only fires on an explicit signal;
'general' is the honest fallback, never a guess.
"""
import re

TAGS = {
  # document types
  "type:protest":      "Protest",
  "type:comment":      "Comment",
  "type:motion":       "Motion",
  "type:application":  "Application / petition",
  "type:order":        "Order",
  "type:notice":       "Notice",
  "type:report":       "Report / study",
  "type:tariff":       "Tariff filing",
  "type:agreement":    "Agreement",
  "type:meeting":      "Meeting / workshop",
  "type:other":        "Other filing",
  # topics (union of the vocabularies the ISO and PUC pages already use)
  "topic:large-load":     "Large load / data centers",
  "topic:interconnection":"Interconnection",
  "topic:storage":        "Energy storage",
  "topic:rates":          "Rates / tariffs",
  "topic:capacity":       "Capacity / resource adequacy",
  "topic:transmission":   "Planning / transmission",
  "topic:markets":        "Markets",
  "topic:reliability":    "Reliability / operations",
  "topic:governance":     "Governance",
  "topic:siting":         "Certificates / siting",
  "topic:environmental":  "Environmental",
  "topic:general":        "General",
  # entities are orthogonal to document type/topic and support cross-venue discovery
  "entity:miso":          "MISO",
}

_TYPE_RULES = [
  ("type:protest",     r"\bprotest\b"),
  ("type:comment",     r"\bcomments?\b"),
  ("type:motion",      r"\bmotion\b"),
  ("type:application", r"\b(application|petition|request for (?:prospective )?(?:tariff )?waiver|certificate of public convenience)\b"),
  ("type:order",       r"\border\b"),
  ("type:notice",      r"\bnotice\b"),
  ("type:report",      r"\b(report|study|statement of|final supplemental environmental impact)\b"),
  ("type:tariff",      r"\b(tariff|compliance filing|section 205)\b"),
  ("type:agreement",   r"\b(interconnection agreement|service agreement|settlement agreement)\b"),
  ("type:meeting",     r"\b(meeting|workshop|webinar|technical conference)\b"),
]

_TOPIC_RULES = [
  ("topic:large-load",      r"\b(data cent(?:er|re)|large load|co-?location|large load interconnection|BYONC)\b"),
  ("topic:interconnection", r"\b(interconnection|generator interconnection|queue)\b"),
  ("topic:storage",         r"\b(battery|storage|BESS)\b"),
  ("topic:rates",           r"\b(rate(?:s|making)?|tariff|fuel (?:factor|cost)|rate adjustment|cost recovery)\b"),
  ("topic:capacity",        r"\b(capacity|resource adequacy|accreditation|IRAS|reliability assurance)\b"),
  ("topic:transmission",    r"\b(transmission|RTEP|planning|network upgrade)\b"),
  ("topic:markets",         r"\b(market|auction|bid|offer cap)\b"),
  ("topic:reliability",     r"\b(reliability|operations|outage|frequency response)\b"),
  ("topic:governance",      r"\b(governance|stakeholder|bylaws|voting)\b"),
  ("topic:siting",          r"\b(certificate of convenience|CPCN|siting|certificate of public convenience)\b"),
  ("topic:environmental",   r"\b(environmental|EIS|emissions?|renewable portfolio)\b"),
]

def _rx(pat): return re.compile(pat, re.I)
_TYPE_RULES = [(t, _rx(p)) for t, p in _TYPE_RULES]
_TOPIC_RULES = [(t, _rx(p)) for t, p in _TOPIC_RULES]

def classify(text, source_class=None):
    """Return list of (tag_id, rule_name). Deterministic, auditable.
    Type rules try the title first (what the filer called it), then the
    source's class field (what the docket office called it)."""
    title = text or ""
    hay = f"{source_class or ''} {title}"
    out = []
    for tag, rx in _TYPE_RULES:
        if rx.search(title):
            out.append((tag, f"title-rx:{tag}")); break
    else:
        for tag, rx in _TYPE_RULES:
            if rx.search(source_class or ""):
                out.append((tag, f"class-rx:{tag}")); break
        else:
            out.append(("type:other", "fallback:no-type-signal"))
    topics = [(t, f"topic-rx:{t}") for t, rx in _TOPIC_RULES if rx.search(hay)]
    out.extend(topics or [("topic:general", "fallback:no-topic-signal")])
    return out
