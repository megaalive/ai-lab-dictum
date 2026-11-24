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
dictum_cli_test(ask_question unsupported ask "${question}")
dictum_cli_test(ask_literal_option unsupported ask --help)
dictum_cli_test(ask_canary unsupported ask "DCT008_CANARY %s; literal")
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
