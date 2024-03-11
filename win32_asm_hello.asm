public win32_return_100

.686p
.XMM
.MODEL FLAT, C
.CODE

; int cdecl win32_return_100()

align 8
win32_return_100 PROC
  mov eax, 100
  ret
win32_return_100 ENDP

END
