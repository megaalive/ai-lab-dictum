"""Independent v2 structural seeds from original v1 fixtures.

These are not authorized chains. V1 fixtures are never rewritten. The new
policy/action structure is proposal-only and version identities are explicit.
"""
import copy
from run import fixture

def chains():
    for row in fixture("chains")["chains"]:
        stages=copy.deepcopy(row["objects"])
        for obj in stages.values():
            obj["schema_version"]=2
            for field in ("catalog","policy"):
                if field in obj:
                    obj[field]["version"]=2
        policy=stages["policy"]
        policy["decision"]="allow-proposal"
        policy["reason"]="proposal-eligible"
        policy["representation"]="structured-proposal"
        ir=stages["ir"]
        stages["plan"]["action"]={"kind":"structured-proposal","operation":{
            "kind":"native","handler":"proposal."+ir["intent"],
            "input_slots":[s["name"] for s in ir["slots"]]}}
        yield stages
