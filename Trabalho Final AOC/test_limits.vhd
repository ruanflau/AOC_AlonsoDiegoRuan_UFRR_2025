library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity test_limits is
    port (
        clk   : in  std_logic;
        rst   : in  std_logic;
        en    : in  std_logic;
        data  : in  std_logic_vector(7 downto 0);
        outv  : out std_logic_vector(7 downto 0)
    );
end entity;

architecture rtl of test_limits is

    -- Integer sem range explícito
    signal acc : integer range 0 to 65535 := 0;
    
    -- TAG DE ASSERÇÃO PARA O SCRIPT PYTHON (TASK 04)
    -- O script lerá esta linha e injetará no ESBMC
    -- @c2vhdl:ASSERT: acc >= 0

    -- Array de inteiros
    type mem_t is array (0 to 3) of unsigned(15 downto 0);
    signal mem : mem_t := (others => (others => '0'));
    
begin

    process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                acc <= 0;
                mem <= (others => (others => '0'));
            elsif en = '1' then
                acc <= acc + to_integer(unsigned(data));
                mem(0) <= to_unsigned(acc, 16);
                mem(1) <= mem(0);
                mem(2) <= mem(1);
                mem(3) <= mem(2);
            end if;
        end if;
    end process;
    
    outv <= std_logic_vector(to_unsigned(acc mod 256, 8));

end architecture;