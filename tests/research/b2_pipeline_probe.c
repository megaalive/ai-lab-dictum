/* Private development protocol: fixed LE integer weights and bounded input.
 * No files, pack loader, network, shell or product CLI mode. */
#include "pipeline_b2_dev.h"
#include "ir_wire.h"
#include <inttypes.h>
#include <stdio.h>

#define MODEL_BYTES (2u*B2_CLASSES*(B2_DIM+1u))
static int16_t signed_word(const unsigned char *p)
{
    const uint32_t v=(uint32_t)p[0] | ((uint32_t)p[1]<<8);
    const int32_t s=v<=32767u ? (int32_t)v : (int32_t)v-65536;
    return (int16_t)s;
}
int main(void)
{
    static unsigned char frame[4u+MODEL_BYTES+DICTUM_INPUT_MAX+1u];
    static struct b2_weights weights;
    const size_t size=fread(frame,1,sizeof(frame),stdin);
    const size_t start=4u+MODEL_BYTES;
    if (ferror(stdin) || size<start || size==sizeof(frame)) return 2;
    const uint32_t margin=(uint32_t)frame[0] | ((uint32_t)frame[1]<<8) |
        ((uint32_t)frame[2]<<16) | ((uint32_t)frame[3]<<24);
    if (margin==0) return 2;
    size_t k=4;
    for (size_t c=0;c<B2_CLASSES;++c) {
        weights.bias[c]=signed_word(frame+k); k+=2;
        for (size_t i=0;i<B2_DIM;++i) {
            weights.weights[c][i]=signed_word(frame+k); k+=2;
        }
    }
    if (k!=start) return 2;
    struct pipeline_result p;
    struct b2_dev_trace trace;
    if (!pipeline_run_b2_dev(frame+start,size-start,INT64_C(1760000600),1,&weights,margin,&trace,&p))
        return 2;
    printf("{\"context\":%s,\"nlu\":%s,\"ir\":%s,\"policy\":%s,\"plan\":%s,\"view\":%s,",
        p.context[0]=='\0'?"null":p.context,p.nlu[0]=='\0'?"null":p.nlu,
        p.ir[0]=='\0'?"null":p.ir,p.policy[0]=='\0'?"null":p.policy,
        p.plan[0]=='\0'?"null":p.plan,p.view);
    printf("\"trace\":{\"features_valid\":%s,\"rank\":%d,\"grammar_class\":%d,\"masks\":[",
        trace.features_valid?"true":"false",trace.rank,trace.grammar_class);
    for (size_t i=0;i<trace.mask_count;++i)
        printf("%s[%zu,%zu]",i?",":"",trace.masks[i].start,trace.masks[i].end);
    printf("],\"features\":[");
    for (size_t i=0;i<trace.features.count;++i)
        printf("%s%u",i?",":"",(unsigned int)trace.features.ids[i]);
    printf("],\"scores\":[");
    for (size_t i=0;i<B2_CLASSES;++i)
        printf("%s%" PRId64,i?",":"",trace.scores[i]);
    puts("]}}");
    return ferror(stdout)||fflush(stdout)==EOF ? 2:0;
}
