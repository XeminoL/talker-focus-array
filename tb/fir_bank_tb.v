`timescale 1ns / 1ps

module fir_bank_tb;

    parameter CHANNELS = 64;
    parameter FRAMES = 300;
    parameter FRAME_CYCLES = 2604;

    reg clk = 1'b0;
    reg rst = 1'b1;
    reg in_valid = 1'b0;
    reg [5:0] in_channel = 0;
    reg signed [23:0] in_sample = 0;
    wire out_valid;
    wire [5:0] out_channel;
    wire signed [23:0] out_sample;

    reg [23:0] stimulus [0:CHANNELS*FRAMES-1];
    integer frame;
    integer channel;
    integer outputs;
    integer file;

    fir_bank dut (
        .clk(clk),
        .rst(rst),
        .in_valid(in_valid),
        .in_channel(in_channel),
        .in_sample(in_sample),
        .out_valid(out_valid),
        .out_channel(out_channel),
        .out_sample(out_sample)
    );

    always #4 clk = ~clk;

    always @(posedge clk) begin
        if (out_valid) begin
            $fdisplay(file, "%0d %0d", out_channel, out_sample);
            outputs = outputs + 1;
        end
    end

    initial begin
        $readmemh("fir_bank_stimulus.hex", stimulus);
        file = $fopen("fir_bank_rtl.txt", "w");
        outputs = 0;
        repeat (4) @(posedge clk);
        rst <= 1'b0;
        for (frame = 0; frame < FRAMES; frame = frame + 1) begin
            for (channel = 0; channel < CHANNELS; channel = channel + 1) begin
                @(posedge clk);
                in_valid   <= 1'b1;
                in_channel <= channel;
                in_sample  <= stimulus[frame * CHANNELS + channel];
            end
            @(posedge clk);
            in_valid <= 1'b0;
            repeat (FRAME_CYCLES - CHANNELS - 1) @(posedge clk);
        end
        repeat (FRAME_CYCLES * 2) @(posedge clk);
        $fclose(file);
        $display("outputs %0d", outputs);
        $finish;
    end

endmodule
