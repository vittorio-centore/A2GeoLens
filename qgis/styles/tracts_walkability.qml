<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34" styleCategories="Symbology|Labeling">
  <renderer-v2 attr="walkability_score" type="graduatedSymbol" graduatedMethod="GraduatedColor" symbollevels="0" forceraster="0" enableorderby="0">
    <ranges>
      <range lower="0" upper="25" label="0 - 25" symbol="0" render="true"/>
      <range lower="25" upper="40" label="25 - 40" symbol="1" render="true"/>
      <range lower="40" upper="55" label="40 - 55" symbol="2" render="true"/>
      <range lower="55" upper="70" label="55 - 70" symbol="3" render="true"/>
      <range lower="70" upper="100" label="70 - 100" symbol="4" render="true"/>
    </ranges>
    <symbols>
      <symbol name="0" type="fill" alpha="1" clip_to_extent="1">
        <layer class="SimpleFill" enabled="1" pass="0">
          <Option type="Map">
            <Option name="color" type="QString" value="68,1,84,210"/>
            <Option name="outline_color" type="QString" value="36,39,37,190"/>
            <Option name="outline_width" type="QString" value="0.3"/>
            <Option name="style" type="QString" value="solid"/>
          </Option>
        </layer>
      </symbol>
      <symbol name="1" type="fill" alpha="1" clip_to_extent="1">
        <layer class="SimpleFill" enabled="1" pass="0">
          <Option type="Map">
            <Option name="color" type="QString" value="59,82,139,210"/>
            <Option name="outline_color" type="QString" value="36,39,37,190"/>
            <Option name="outline_width" type="QString" value="0.3"/>
            <Option name="style" type="QString" value="solid"/>
          </Option>
        </layer>
      </symbol>
      <symbol name="2" type="fill" alpha="1" clip_to_extent="1">
        <layer class="SimpleFill" enabled="1" pass="0">
          <Option type="Map">
            <Option name="color" type="QString" value="33,145,140,210"/>
            <Option name="outline_color" type="QString" value="36,39,37,190"/>
            <Option name="outline_width" type="QString" value="0.3"/>
            <Option name="style" type="QString" value="solid"/>
          </Option>
        </layer>
      </symbol>
      <symbol name="3" type="fill" alpha="1" clip_to_extent="1">
        <layer class="SimpleFill" enabled="1" pass="0">
          <Option type="Map">
            <Option name="color" type="QString" value="94,201,98,210"/>
            <Option name="outline_color" type="QString" value="36,39,37,190"/>
            <Option name="outline_width" type="QString" value="0.3"/>
            <Option name="style" type="QString" value="solid"/>
          </Option>
        </layer>
      </symbol>
      <symbol name="4" type="fill" alpha="1" clip_to_extent="1">
        <layer class="SimpleFill" enabled="1" pass="0">
          <Option type="Map">
            <Option name="color" type="QString" value="253,231,37,210"/>
            <Option name="outline_color" type="QString" value="36,39,37,190"/>
            <Option name="outline_width" type="QString" value="0.3"/>
            <Option name="style" type="QString" value="solid"/>
          </Option>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <labeling type="simple">
    <settings>
      <text-style fieldName="tract_label" fontFamily="Arial" fontSize="8" fontWeight="50" namedStyle="Regular" textColor="36,39,37,255"/>
      <text-format multilineHeight="1" wrapChar=""/>
      <placement placement="1" centroidWhole="1"/>
    </settings>
  </labeling>
</qgis>

