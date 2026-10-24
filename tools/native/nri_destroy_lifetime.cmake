if(NOT NRI_SOURCE_DIR)
    message(FATAL_ERROR "NRI_SOURCE_DIR is required")
endif()
set(_header "${NRI_SOURCE_DIR}/Source/Shared/DeviceBase.h")
file(READ "${_header}" _source)
set(_old [=[        object->~T();

        const auto& allocationCallbacks = ((DeviceBase&)(object->GetDevice())).GetAllocationCallbacks();]=])
set(_new [=[        // Copy callbacks while the object and its device reference are alive.
        const auto allocationCallbacks = ((DeviceBase&)(object->GetDevice())).GetAllocationCallbacks();
        object->~T();]=])
string(FIND "${_source}" "${_new}" _already)
if(NOT _already EQUAL -1)
    return()
endif()
string(FIND "${_source}" "${_old}" _position)
if(_position EQUAL -1)
    message(FATAL_ERROR "NRI destruction context changed; review lifetime patch")
endif()
string(REPLACE "${_old}" "${_new}" _source "${_source}")
file(WRITE "${_header}" "${_source}")
