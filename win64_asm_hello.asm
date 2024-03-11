public win64_return_100

.CODE

; int cdecl win64_return_100()

align 8
win64_return_100 PROC
  mov rax, 100
  ret
win64_return_100 ENDP

END
