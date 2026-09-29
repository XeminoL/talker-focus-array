`timescale 1ns / 1ps

module cic_decimator_tb;

    parameter SAMPLES = 256000;

    reg clk = 1'b0;
    reg rst = 1'b1;
    reg pdm_valid = 1'b0;
    reg pdm_bit = 1'b0;
    wire sample_valid;
    wire signed [31:0] sample;

    reg stimulus [0:SAMPLES-1];
    integer index;
    integer outputs;
    integer file;

    cic_decimator dut (
        .clk(clk),
        .rst(rst),
        .pdm_valid(pdm_valid),
        .pdm_bit(pdm_bit),
        .sample_valid(sample_valid),
        .sample(sample)
    );

    always #4 clk = ~clk;

    always @(posedge clk) begin
        if (sample_valid) begin
            $fdisplay(file, "%0d", sample);
            outputs = outputs + 1;
        end
    end

    initial begin
        $readmemb("cic_stimulus.txt", stimulus);
        file = $fopen("cic_rtl.txt", "w");
        outputs = 0;
        repeat (4) @(posedge clk);
        rst <= 1'b0;
        for (index = 0; index < SAMPLES; index = index + 1) begin
            @(posedge clk);
            pdm_valid <= 1'b1;
            pdm_bit   <= stimulus[index];
            @(posedge clk);
            pdm_valid <= 1'b0;
        end
        repeat (4) @(posedge clk);
        $fclose(file);
        $display("outputs %0d", outputs);
        $finish;
    end

endmodule
