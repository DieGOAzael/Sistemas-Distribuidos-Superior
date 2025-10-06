/* Archivo rand.x */
struct inputs{
float i;
float j;
char operator;
};

program CALCULATE_PROG{
version CALCULATE_VERS{
float SUM (inputs) = 1;
float RES (inputs) = 2;
float MUL (inputs) = 3;
float DIV (inputs) = 4;
} = 1;
} = 0x2fffffff;
