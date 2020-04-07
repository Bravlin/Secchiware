// It should crash if there is no debbuger attached

int main()
{
    asm(
        "xor %eax, %eax\n"
        "int $0x2d\n"
        "nop"
    );
    return 0;
}
