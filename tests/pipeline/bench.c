/* Development benchmark only; separate process for each model. */
#define _POSIX_C_SOURCE 200809L
#include "pipeline.h"
#include "ir_wire.h"
#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>

#define CASES 140u
#define REPEATS 10u

int main(int argc,char *argv[])
{
    enum pipeline_model model;
    if (argc!=2) return 2;
    if (strcmp(argv[1],"B0")==0) model=PIPE_B0;
    else if (strcmp(argv[1],"B1")==0) model=PIPE_B1;
    else return 2;
    unsigned char input[DICTUM_INPUT_MAX+1u];
    struct pipeline_result result;
    uint64_t sequence=1;
    for (unsigned int rep=0;rep<=REPEATS;++rep) {
        for (unsigned int i=0;i<CASES;++i) {
            unsigned char header[4];
            if (fread(header,1,sizeof(header),stdin)!=sizeof(header)) return 2;
            const uint32_t size=(uint32_t)header[0]|((uint32_t)header[1]<<8)|
                ((uint32_t)header[2]<<16)|((uint32_t)header[3]<<24);
            if (size>sizeof(input)||fread(input,1,size,stdin)!=size) return 2;
            struct timespec before,after;
            if (clock_gettime(CLOCK_MONOTONIC,&before)!=0) return 2;
            if (!pipeline_run(input,size,INT64_C(1760000600),sequence++,model,&result)) return 2;
            if (clock_gettime(CLOCK_MONOTONIC,&after)!=0) return 2;
            if (result.outcome==PIPE_INTERNAL) return 2;
            const int64_t secs=(int64_t)after.tv_sec-(int64_t)before.tv_sec;
            if (secs<0||secs>60) return 2;
            const int64_t ns=secs*INT64_C(1000000000)+(int64_t)after.tv_nsec-(int64_t)before.tv_nsec;
            if (ns<0) return 2;
            if (rep!=0 && printf("%u %u %" PRId64 " %d\n",rep,i,ns,(int)result.outcome)<0) return 2;
        }
    }
    if (fgetc(stdin)!=EOF||ferror(stdin)) return 2;
    struct rusage usage;
    if (getrusage(RUSAGE_SELF,&usage)!=0||usage.ru_maxrss<=0) return 2;
    if (printf("RSS_KIB %ld\n",usage.ru_maxrss)<0) return 2;
    return fflush(stdout)==EOF?2:0;
}
