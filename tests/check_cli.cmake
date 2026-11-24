cmake_minimum_required(VERSION 3.24)

set(expected_stdout "")
set(expected_stderr "")

if(EXPECT STREQUAL "help")
    set(expected_code 0)
    set(expected_stdout [=[Dictum - fondasi runtime lokal

  dictum --help           Tampilkan bantuan.
  dictum --version        Tampilkan versi.
  dictum ask "instruksi"  Terjemahan belum tersedia.
  dictum run "instruksi"  Eksekusi dinonaktifkan.
]=])
elseif(EXPECT STREQUAL "version")
    set(expected_code 0)
    set(expected_stdout "dictum ${VERSION}\n")
elseif(EXPECT STREQUAL "invalid")
    set(expected_code 2)
    set(expected_stderr "dictum: argumen tidak valid. Gunakan --help.\n")
elseif(EXPECT STREQUAL "unsupported")
    set(expected_code 3)
    set(expected_stderr "dictum: unsupported. Terjemahan instruksi belum tersedia.\n")
elseif(EXPECT STREQUAL "denied")
    set(expected_code 4)
    set(expected_stderr "dictum: eksekusi ditolak (proposal-only).\n")
else()
    message(FATAL_ERROR "Kategori hasil uji tidak dikenal: ${EXPECT}")
endif()

set(stdout_path "${CMAKE_CURRENT_BINARY_DIR}/${CASE}.stdout")
set(stderr_path "${CMAKE_CURRENT_BINARY_DIR}/${CASE}.stderr")
set(capture RESULT_VARIABLE code OUTPUT_FILE "${stdout_path}" ERROR_FILE "${stderr_path}" TIMEOUT 5)

# Kutip setiap token agar argumen kosong tetap diteruskan ke executable.
if(NARGS EQUAL 3)
    execute_process(COMMAND "${DICTUM}" "${ARG1}" "${ARG2}" "${ARG3}" ${capture})
elseif(NARGS EQUAL 2)
    execute_process(COMMAND "${DICTUM}" "${ARG1}" "${ARG2}" ${capture})
elseif(NARGS EQUAL 1)
    execute_process(COMMAND "${DICTUM}" "${ARG1}" ${capture})
elseif(NARGS EQUAL 0)
    execute_process(COMMAND "${DICTUM}" ${capture})
else()
    message(FATAL_ERROR "Harness mendukung nol hingga tiga argumen.")
endif()

if(CMAKE_HOST_WIN32)
    string(REPLACE "\n" "\r\n" expected_stdout "${expected_stdout}")
    string(REPLACE "\n" "\r\n" expected_stderr "${expected_stderr}")
endif()
string(HEX "${expected_stdout}" expected_stdout_hex)
string(HEX "${expected_stderr}" expected_stderr_hex)
file(READ "${stdout_path}" output_hex HEX)
file(READ "${stderr_path}" diagnostic_hex HEX)

if(NOT "${code}" STREQUAL "${expected_code}"
   OR NOT "${output_hex}" STREQUAL "${expected_stdout_hex}"
   OR NOT "${diagnostic_hex}" STREQUAL "${expected_stderr_hex}")
    message(FATAL_ERROR
        "Exit aktual [${code}], diharapkan [${expected_code}]\n"
        "stdout hex aktual [${output_hex}], diharapkan [${expected_stdout_hex}]\n"
        "stderr hex aktual [${diagnostic_hex}], diharapkan [${expected_stderr_hex}]")
endif()
