#ifndef DICTUM_IR_SCHEMA_H
#define DICTUM_IR_SCHEMA_H
#include "ir_wire.h"
enum ir_stage { IR_NLU, IR_RESOLVED, IR_POLICY, IR_PLAN };
/* Structure only; never an authorization or semantic verdict. */
enum ir_status ir_validate(const struct ir_document *doc, enum ir_stage stage);
#endif
