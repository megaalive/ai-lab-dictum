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
