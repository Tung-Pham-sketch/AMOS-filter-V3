from rules.rule_loader import rule_loader

def get_ref_keywords():
    return rule_loader.get_keywords("REF")

def get_iaw_keywords():
    return rule_loader.get_keywords("IAW")

def get_header_skip_keywords():
    return rule_loader.get_keywords("HEADER_SKIP")
