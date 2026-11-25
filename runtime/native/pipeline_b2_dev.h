#ifndef DICTUM_PIPELINE_B2_DEV_H
#define DICTUM_PIPELINE_B2_DEV_H
#include "pipeline.h"
#include "b2_linear.h"

/* Only compiled into research/b2_pipeline_probe. No product model loader. */
struct b2_dev_trace {
    bool features_valid;
    int rank, grammar_class; /* Zero-based canonical registry ordinal; -1 abstain. */
    size_t mask_count;
    struct b2_span masks[B2_MASK_MAX];
    struct b2_features features;
    int64_t scores[B2_CLASSES];
};
bool pipeline_run_b2_dev(const unsigned char *input,size_t size,int64_t reference_unix_s,
                  uint64_t request_sequence,const struct b2_weights *weights,uint32_t margin,
                  struct b2_dev_trace *trace,struct pipeline_result *out);
#endif
