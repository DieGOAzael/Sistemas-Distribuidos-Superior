#include "calculate.h"

//funcion principal
float calculate_prog_1(char *host, float n1, float n2, char opr, CLIENT *clnt)
{
    float *result_1; //apuntador a resultado con entradas para
    inputs add_1_arg; //datos de entrada para suma
    float *result_2; //apuntador a resultado con entradas para
    inputs sub_1_arg; //datos de entrada para resta
    float *result_3; //apuntador a resultado con entradas para
    inputs mul_1_arg; //datos de entrada para multiplicacion
    float *result_4; //apuntador a resultado con entradas para
    inputs div_1_arg; //datos de entrada para division

    if (opr == '+') { //si el operador ingresado es +, realizara las siguientes acciones
        add_1_arg.i = n1;
        add_1_arg.j = n2;
        add_1_arg.operator = opr;

        result_1 = sum_1(&add_1_arg, clnt);
        if (result_1 == (float *) NULL) {
            clnt_perror(clnt, "Llamada fallida");
        }
        return *result_1;
    }

    else if (opr == '-') { //si el operador ingresado es -, realizara las siguientes acciones
        sub_1_arg.i = n1;
        sub_1_arg.j = n2;
        sub_1_arg.operator = opr;

        result_2 = res_1(&sub_1_arg, clnt);
        if (result_2 == (float *) NULL) {
            clnt_perror(clnt, "Llamada fallida");
        }
        return *result_2;
    }

    else if (opr == '*') { //si el operador ingresado es *, realizara las siguientes acciones
        mul_1_arg.i = n1;
        mul_1_arg.j = n2;
        mul_1_arg.operator = opr;

        result_3 = mul_1(&mul_1_arg, clnt);
        if (result_3 == (float *) NULL) {
            clnt_perror(clnt, "Llamada fallida");
        }
        return *result_3;
    }

    else if (opr == '/') { //si el operador ingresado es /, realizara las siguientes acciones
        div_1_arg.i = n1;
        div_1_arg.j = n2;
        div_1_arg.operator = opr;

        if (n2 == 0) { //si la variable n2 es 0 mandara el siguiente mensaje
            printf("Division entre cero no es valida.\n");
            exit(0);
        } else { //de lo contrario realizara la operacion con el siguiente codigo
            result_4 = div_1(&div_1_arg, clnt);
            if (result_4 == (float *) NULL) {
                clnt_perror(clnt, "Llamada fallida");
            }
            return *result_4;
        }
    }

    else {
        printf("Operador no valido.\n");
        return 0.0;
    }
}

//funcion main
int main (int argc, char *argv[])
{
    char *host;
    float a,b;
    char op;
    CLIENT *clnt;

    if (argc < 2) {
        printf("usage: %s server_host\n", argv[0]);
        exit(1);
    }

    printf("Bienvenido a Calculadora RPC!!!\n"); //mensaje de bienvenida
    printf("+ para Suma\n- para Resta\n* para Multiplicacion\n/ para Division\n"); //mensaje para las opciones de operacion
    printf("Teclee el 1er numero :\n"); //mensaje para teclear el primer numero
    scanf("%f",&a); //guarda el primer numero en la variable a
    printf("Teclee el 2do numero:\n"); //mensaje para teclear el segundo numero
    scanf("%f",&b); //guarda el segundo numero en la variable b
    printf("Teclee el Operador :\n"); //mensaje para teclear el operador
    scanf(" %c",&op); //el operador lo guarda en la variable op

    host = argv[1];

    clnt = clnt_create(host, CALCULATE_PROG, CALCULATE_VERS, "udp"); //se crea la variable cliente con sus parámetros

    if (clnt == NULL) {
        clnt_pcreateerror(host);
        exit(1);
    }

    printf("La Respuesta es = %.2f\n", calculate_prog_1(host,a,b,op,clnt)); //mensaje del resultado

    clnt_destroy(clnt); // se destruye el cliente
    exit(0); // se finaliza el programa
}

