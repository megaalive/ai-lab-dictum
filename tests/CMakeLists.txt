function(dictum_cli_test name expected)
    math(EXPR nargs "${ARGC} - 2")
    add_test(NAME "cli.${name}"
        COMMAND "${CMAKE_COMMAND}"
            "-DDICTUM=$<TARGET_FILE:dictum>"
            "-DVERSION=${DICTUM_VERSION}"
            "-DCASE=${name}"
            "-DEXPECT=${expected}"
            "-DNARGS=${nargs}"
            "-DARG1=${ARGV2}"
            "-DARG2=${ARGV3}"
            "-DARG3=${ARGV4}"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/check_cli.cmake"
    )
endfunction()

set(question "siapa yang menggunakan port 5432?")

dictum_cli_test(help help --help)
dictum_cli_test(version version --version)
dictum_cli_test(no_args invalid)
dictum_cli_test(empty_arg invalid "")
dictum_cli_test(unknown_arg invalid --help-DCT008_CANARY)
dictum_cli_test(help_extra invalid --help ask)
dictum_cli_test(version_extra invalid --version run)
dictum_cli_test(ask_missing invalid ask)
dictum_cli_test(ask_empty invalid ask "")
dictum_cli_test(ask_extra invalid ask siapa yang)
dictum_cli_test(run_question denied run "${question}")
dictum_cli_test(run_missing denied run)
dictum_cli_test(run_extra denied run --version DCT008_CANARY)

add_executable(ir_probe ir/native_probe.c)
target_link_libraries(ir_probe PRIVATE dictum_ir)
set_target_properties(ir_probe PROPERTIES C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
target_compile_options(ir_probe PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
    -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla)
if(dictum_sanitizers)
    target_compile_options(ir_probe PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
    if(DICTUM_ENABLE_UBSAN)
        target_compile_options(ir_probe PRIVATE -fno-sanitize-recover=undefined)
    endif()
endif()
add_test(NAME ir.differential COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/ir/differential.py" "$<TARGET_FILE:ir_probe>")
set_tests_properties(ir.differential PROPERTIES TIMEOUT 180)

add_executable(ir_span ir/span.c)
target_link_libraries(ir_span PRIVATE dictum_ir)
set_target_properties(ir_span PROPERTIES C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
target_compile_options(ir_span PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
    -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla)
if(dictum_sanitizers)
    target_compile_options(ir_span PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
    if(DICTUM_ENABLE_UBSAN)
        target_compile_options(ir_span PRIVATE -fno-sanitize-recover=undefined)
    endif()
endif()
add_test(NAME ir.span COMMAND ir_span)

add_test(NAME ir.digest COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/ir/digest.py" "$<TARGET_FILE:ir_probe>")
set_tests_properties(ir.digest PROPERTIES TIMEOUT 60)

add_executable(pipeline_probe ir/pipeline_probe.c)
target_link_libraries(pipeline_probe PRIVATE dictum_pipeline)
set_target_properties(pipeline_probe PROPERTIES C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
target_compile_options(pipeline_probe PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
    -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla)
if(dictum_sanitizers)
    target_compile_options(pipeline_probe PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
    if(DICTUM_ENABLE_UBSAN)
        target_compile_options(pipeline_probe PRIVATE -fno-sanitize-recover=undefined)
    endif()
endif()

add_test(NAME pipeline.functional COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/pipeline/run.py" "$<TARGET_FILE:pipeline_probe>" "$<TARGET_FILE:dictum>")
set_tests_properties(pipeline.functional PROPERTIES TIMEOUT 180)

add_executable(renderer_probe renderer/native_fixture.c)
target_link_libraries(renderer_probe PRIVATE dictum_pipeline)
set_target_properties(renderer_probe PROPERTIES C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
target_compile_options(renderer_probe PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
    -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla)
if(dictum_sanitizers)
    target_compile_options(renderer_probe PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
    if(DICTUM_ENABLE_UBSAN)
        target_compile_options(renderer_probe PRIVATE -fno-sanitize-recover=undefined)
    endif()
endif()
add_test(NAME renderer.native COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/renderer/native_run.py" "$<TARGET_FILE:renderer_probe>")
set_tests_properties(renderer.native PROPERTIES TIMEOUT 90)

add_executable(pipeline_bench pipeline/bench.c)
target_link_libraries(pipeline_bench PRIVATE dictum_pipeline)
set_target_properties(pipeline_bench PROPERTIES C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
target_compile_options(pipeline_bench PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
    -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla)
if(dictum_sanitizers)
    target_compile_options(pipeline_bench PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
    if(DICTUM_ENABLE_UBSAN)
        target_compile_options(pipeline_bench PRIVATE -fno-sanitize-recover=undefined)
    endif()
endif()
add_test(NAME pipeline.benchmark COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/pipeline/bench.py" "$<TARGET_FILE:pipeline_bench>")
set_tests_properties(pipeline.benchmark PROPERTIES TIMEOUT 120)

add_test(NAME pipeline.s2_regression COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/pipeline/s2_regression.py" "$<TARGET_FILE:pipeline_probe>" "$<TARGET_FILE:dictum>")
set_tests_properties(pipeline.s2_regression PROPERTIES TIMEOUT 120)

add_test(NAME catalog.native_lookup COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/pipeline/catalog_lookup.py" "$<TARGET_FILE:dictum>")
set_tests_properties(catalog.native_lookup PROPERTIES TIMEOUT 90)

add_test(NAME pipeline.f1_functional COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/pipeline/f1_functional.py" "$<TARGET_FILE:pipeline_probe>" "$<TARGET_FILE:dictum>")
set_tests_properties(pipeline.f1_functional PROPERTIES TIMEOUT 240)

add_test(NAME pipeline.f1_benchmark COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/pipeline/bench.py" "$<TARGET_FILE:pipeline_bench>" f1-functional-v1.json)
set_tests_properties(pipeline.f1_benchmark PROPERTIES TIMEOUT 120)

# Development-only candidate-v2 fixture validator; not linked into product.
set(f1_candidate_generated "${CMAKE_CURRENT_BINARY_DIR}/f1_candidate_generated.inc")
add_custom_command(OUTPUT "${f1_candidate_generated}"
    COMMAND "${Python3_EXECUTABLE}" -B "${PROJECT_SOURCE_DIR}/tools/generate_f1_candidates.py" "${f1_candidate_generated}"
    DEPENDS "${PROJECT_SOURCE_DIR}/tools/generate_f1_candidates.py"
        "${PROJECT_SOURCE_DIR}/tools/f1_slot_domains.py"
        "${PROJECT_SOURCE_DIR}/spec/catalog/f1-slot-domains-v1.json"
        "${PROJECT_SOURCE_DIR}/spec/catalog/f1-slot-candidate-v2.schema.json"
        "${PROJECT_SOURCE_DIR}/catalog/core/intents-v1.json"
        "${PROJECT_SOURCE_DIR}/catalog/debian-13/v1.json"
    VERBATIM)
add_executable(f1_candidate_probe ir/f1_candidate_probe.c
    "${PROJECT_SOURCE_DIR}/runtime/native/f1_candidate.c" "${f1_candidate_generated}")
target_include_directories(f1_candidate_probe PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_link_libraries(f1_candidate_probe PRIVATE dictum_ir)
set_target_properties(f1_candidate_probe PROPERTIES C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
target_compile_options(f1_candidate_probe PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
    -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla)
if(dictum_sanitizers)
    target_compile_options(f1_candidate_probe PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
    if(DICTUM_ENABLE_UBSAN)
        target_compile_options(f1_candidate_probe PRIVATE -fno-sanitize-recover=undefined)
    endif()
endif()
add_test(NAME ir.f1_candidate_diff COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/ir/f1_candidate_diff.py" "$<TARGET_FILE:f1_candidate_probe>" "$<TARGET_FILE:ir_probe>")
set_tests_properties(ir.f1_candidate_diff PROPERTIES TIMEOUT 120)

add_test(NAME pipeline.f1_v2_functional COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/pipeline/f1_v2_functional.py" "$<TARGET_FILE:pipeline_probe>" "$<TARGET_FILE:dictum>")
set_tests_properties(pipeline.f1_v2_functional PROPERTIES TIMEOUT 240)
add_test(NAME pipeline.f1_v2_benchmark COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/pipeline/bench.py" "$<TARGET_FILE:pipeline_bench>" f1-v2-functional.json)
set_tests_properties(pipeline.f1_v2_benchmark PROPERTIES TIMEOUT 120)

add_test(NAME ir.v2_differential COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/ir/v2_differential.py" "$<TARGET_FILE:ir_probe>")
set_tests_properties(ir.v2_differential PROPERTIES TIMEOUT 180)
add_test(NAME pipeline.v2_semantic_mutations COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/pipeline/v2_semantic_mutations.py" "$<TARGET_FILE:pipeline_probe>" "$<TARGET_FILE:dictum>")
set_tests_properties(pipeline.v2_semantic_mutations PROPERTIES TIMEOUT 90)

# B2 development mechanics only; no link to product CLI or pipeline.
add_executable(b2_probe research/b2_probe.c "${PROJECT_SOURCE_DIR}/runtime/native/b2_linear.c")
target_link_libraries(b2_probe PRIVATE dictum_ir)
set_target_properties(b2_probe PROPERTIES C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
target_compile_options(b2_probe PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
    -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla)
if(dictum_sanitizers)
    target_compile_options(b2_probe PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
    if(DICTUM_ENABLE_UBSAN)
        target_compile_options(b2_probe PRIVATE -fno-sanitize-recover=undefined)
    endif()
endif()
add_test(NAME research.b2_mechanics COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/research/b2_linear.py" "$<TARGET_FILE:b2_probe>")
set_tests_properties(research.b2_mechanics PROPERTIES TIMEOUT 120)

# Separate research executable compiles the identical native pipeline with
# an explicitly test-only B2 guard. Product dictum_pipeline has no B2 link.
add_executable(b2_pipeline_probe research/b2_pipeline_probe.c
    "${PROJECT_SOURCE_DIR}/runtime/native/pipeline.c"
    "${PROJECT_SOURCE_DIR}/runtime/native/b2_linear.c")
add_dependencies(b2_pipeline_probe dictum_pipeline)
target_include_directories(b2_pipeline_probe PRIVATE "${PROJECT_BINARY_DIR}")
target_compile_definitions(b2_pipeline_probe PRIVATE DICTUM_DEV_B2=1)
target_link_libraries(b2_pipeline_probe PRIVATE dictum_pipeline)
set_target_properties(b2_pipeline_probe PROPERTIES C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
target_compile_options(b2_pipeline_probe PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
    -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla)
if(dictum_sanitizers)
    target_compile_options(b2_pipeline_probe PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
    if(DICTUM_ENABLE_UBSAN)
        target_compile_options(b2_pipeline_probe PRIVATE -fno-sanitize-recover=undefined)
    endif()
endif()
add_test(NAME research.b2_common_extractor COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/research/b2_pipeline.py" "$<TARGET_FILE:pipeline_probe>"
    "$<TARGET_FILE:dictum>" "$<TARGET_FILE:b2_pipeline_probe>")
set_tests_properties(research.b2_common_extractor PROPERTIES TIMEOUT 240)

add_test(NAME research.f1_comparator_native_smoke COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/research/f1_compare_native_smoke.py" "$<TARGET_FILE:pipeline_probe>"
    "$<TARGET_FILE:dictum>" "$<TARGET_FILE:b2_pipeline_probe>")
set_tests_properties(research.f1_comparator_native_smoke PROPERTIES TIMEOUT 120)

# Research-only composition prototypes. Do not modify product dictum_pipeline.
function(dictum_composition_probe target source)
    add_executable(${target} ${source} "${PROJECT_SOURCE_DIR}/runtime/native/pipeline.c" ${ARGN})
    add_dependencies(${target} dictum_pipeline)
    target_include_directories(${target} PRIVATE "${PROJECT_BINARY_DIR}")
    target_compile_definitions(${target} PRIVATE DICTUM_DEV_COMPOSE=1)
    target_link_libraries(${target} PRIVATE dictum_pipeline)
    set_target_properties(${target} PROPERTIES C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
        -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla)
    if(dictum_sanitizers)
        target_compile_options(${target} PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
        if(DICTUM_ENABLE_UBSAN)
            target_compile_options(${target} PRIVATE -fno-sanitize-recover=undefined)
        endif()
    endif()
endfunction()
dictum_composition_probe(composition_pipeline_probe ir/pipeline_probe.c)
dictum_composition_probe(composition_b2_probe research/b2_pipeline_probe.c
    "${PROJECT_SOURCE_DIR}/runtime/native/b2_linear.c")
target_compile_definitions(composition_b2_probe PRIVATE DICTUM_DEV_B2=1)
add_test(NAME research.composition_boundary COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/research/f1_composition.py" "$<TARGET_FILE:pipeline_probe>"
    "$<TARGET_FILE:dictum>" "$<TARGET_FILE:composition_pipeline_probe>" "$<TARGET_FILE:composition_b2_probe>")
set_tests_properties(research.composition_boundary PROPERTIES TIMEOUT 180)
