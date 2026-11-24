#ifndef DICTUM_F1_CANDIDATE_H
#define DICTUM_F1_CANDIDATE_H
#include "ir_wire.h"

/* Standalone candidate-v2 synthetic value check, not native IR v2 ingestion.
 * Accepts only exact build-pinned domain fixtures. No authority, resolver,
 * target operation or cross-slot validation. Test/development link only. */
enum ir_status f1_candidate_validate(const struct ir_document *doc);
#endif
