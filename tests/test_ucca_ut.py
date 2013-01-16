"""Testing code for the ucca package, unit-testing only."""

import unittest
import operator
import xml.etree.ElementTree as ETree

from ucca import core, layer0, layer1, convert


class CoreTests(unittest.TestCase):

    @staticmethod
    def _create_basic_passage():
        """Creates a basic :class:Passage to tinker with.

        Passage structure is as follows:
            Layer1: order by ID, heads = [1.2], all = [1.1, 1.2, 1.3]
            Layer2: order by node unique ID descending,
                    heads = all = [2.2, 2.1], attrib={'test': True}
            Nodes (tag):
                1.1 (1)
                1.3 (3), attrib={'node': True}
                1.2 (x), order by edge tag
                    children: 1.3 Edge: tag=test1, attrib={'Edge': True}
                              1.1 Edge: tag=test2
                2.1 (2), children [1.1, 1.2] with edge tags [test, test2]
                2.2 (2), children [1.1, 1.2, 1.3] with tags [test, test1, test]

        """
        p = core.Passage(ID='1')
        l1 = core.Layer(ID='1', root=p)
        l1 = core.Layer(ID='2', root=p, attrib={'test': True},
                        orderkey=lambda x: -1 * int(x.ID.split('.')[1]))

        # Order is explicitly different in order to break the alignment between
        # the ID/Edge ordering and the order of creation/addition
        node11 = core.Node(ID='1.1', root=p, tag='1')
        node13 = core.Node(ID='1.3', root=p, tag='3', attrib={'node': True})
        node12 = core.Node(ID='1.2', root=p, tag='x',
                           orderkey=operator.attrgetter('tag'))
        node21 = core.Node(ID='2.1', root=p, tag='2')
        node22 = core.Node(ID='2.2', root=p, tag='2')
        node12.add('test2', node11)
        node12.add('test1', node13, edge_attrib={'edge': True})
        node21.add('test2', node12)
        node21.add('test', node11)
        node22.add('test1', node12)
        node22.add('test', node13)
        node22.add('test', node11)
        return p

    def test_creation(self):

        p = self._create_basic_passage()

        self.assertEqual(p.ID, '1')
        self.assertEqual(p.root, p)
        self.assertDictEqual(p.attrib.copy(), {})
        self.assertEqual(p.layer('1').ID, '1')
        self.assertEqual(p.layer('2').ID, '2')
        self.assertRaises(KeyError, p.layer, '3')

        l1 = p.layer('1')
        l2 = p.layer('2')
        self.assertEqual(l1.root, p)
        self.assertEqual(l2.attrib['test'], True)
        self.assertNotEqual(l1.orderkey, l2.orderkey)
        self.assertSequenceEqual([x.ID for x in l1.all], ['1.1', '1.2', '1.3'])
        self.assertSequenceEqual([x.ID for x in l1.heads], ['1.2'])
        self.assertSequenceEqual([x.ID for x in l2.all], ['2.2', '2.1'])
        self.assertSequenceEqual([x.ID for x in l2.heads], ['2.2', '2.1'])

        node11, node12, node13 = l1.all
        node22, node21 = l2.all
        self.assertEqual(node11.ID, '1.1')
        self.assertEqual(node11.root, p)
        self.assertEqual(node11.layer.ID, '1')
        self.assertEqual(node11.tag, '1')
        self.assertEqual(len(node11), 0)
        self.assertSequenceEqual(node11.parents, [node12, node21, node22])
        self.assertSequenceEqual(node13.parents, [node12, node22])
        self.assertDictEqual(node13.attrib.copy(), {'node': True})
        self.assertEqual(len(node12), 2)
        self.assertSequenceEqual([x.child for x in node12], [node13, node11])
        self.assertDictEqual(node12[0].attrib.copy(), {'edge': True})
        self.assertSequenceEqual(node12.parents, [node22, node21])
        self.assertEqual(node21[0].ID, '2.1->1.1')
        self.assertEqual(node21[1].ID, '2.1->1.2')
        self.assertEqual(node22[0].ID, '2.2->1.1')
        self.assertEqual(node22[1].ID, '2.2->1.2')
        self.assertEqual(node22[2].ID, '2.2->1.3')

    def test_modifying(self):

        p = self._create_basic_passage()
        l1, l2 = p.layer('1'), p.layer('2')
        node11, node12, node13 = l1.all
        node22, node21 = l2.all

        # Testing attribute changes
        p.attrib['passage'] = 1
        self.assertDictEqual(p.attrib.copy(), {'passage': 1})
        del l2.attrib['test']
        self.assertDictEqual(l2.attrib.copy(), {})
        node13.attrib[1] = 1
        self.assertDictEqual(node13.attrib.copy(), {'node': True, 1: 1})
        self.assertEqual(len(node13.attrib), 2)
        self.assertEqual(node13.attrib.get('node'), True)
        self.assertEqual(node13.attrib.get('missing'), None)

        # Testing Node changes
        node14 = core.Node(ID='1.4', root=p, tag='4')
        node15 = core.Node(ID='1.5', root=p, tag='5')
        self.assertSequenceEqual(l1.all, [node11, node12, node13, node14,
                                          node15])
        self.assertSequenceEqual(l1.heads, [node12, node14, node15])
        node15.add('test', node11)
        self.assertSequenceEqual(node11.parents, [node12, node15, node21,
                                                 node22])
        node21.remove(node12)
        node21.remove(node21[0])
        self.assertEqual(len(node21), 0)
        self.assertSequenceEqual(node12.parents, [node22])
        self.assertSequenceEqual(node11.parents, [node12, node15, node22])
        node14.add('test', node15)
        self.assertSequenceEqual(l1.heads, [node12, node14])
        node12.destroy()
        self.assertSequenceEqual(l1.heads, [node13, node14])
        self.assertSequenceEqual([x.child for x in node22], [node11, node13])


class Layer0Tests(unittest.TestCase):
    """Tests module layer0 functionality."""

    def test_terminals(self):
        """Tests :class:layer0.Terminal new and inherited functionality."""
        p = core.Passage('1')
        l0 = layer0.Layer0(p)
        terms = []
        terms.append(layer0.Terminal(ID='0.1', root=p,
                                     tag=layer0.NodeTags.Word,
                                     attrib={'text': '1',
                                             'paragraph': 1,
                                             'paragraph_position': 1}))
        terms.append(layer0.Terminal(ID='0.2', root=p,
                                     tag=layer0.NodeTags.Word,
                                     attrib={'text': '2',
                                             'paragraph': 2,
                                             'paragraph_position': 1}))
        terms.append(layer0.Terminal(ID='0.3', root=p,
                                     tag=layer0.NodeTags.Punct,
                                     attrib={'text': '.',
                                             'paragraph': 2,
                                             'paragraph_position': 2}))

        self.assertSequenceEqual([t.punct for t in terms],
                                 [False, False, True])
        self.assertSequenceEqual([t.text for t in terms], ['1', '2', '.'])
        self.assertSequenceEqual([t.position for t in terms], [1, 2, 3])
        self.assertSequenceEqual([t.paragraph for t in terms], [1, 2, 2])
        self.assertSequenceEqual([t.para_pos for t in terms], [1, 1, 2])
        self.assertFalse(terms[0] == terms[1])
        self.assertFalse(terms[0] == terms[2])
        self.assertFalse(terms[1] == terms[2])
        self.assertTrue(terms[0] == terms[0])

    def test_layer0(self):
        p = core.Passage('1')
        l0 = layer0.Layer0(p)
        t1 = l0.add_terminal(text='1', punct=False)
        t2 = l0.add_terminal(text='2', punct=True, paragraph=2)
        t3 = l0.add_terminal(text='3', punct=False, paragraph=2)
        self.assertSequenceEqual([x[0] for x in l0.pairs], [1, 2, 3])
        self.assertSequenceEqual([t.para_pos for t in l0.all], [1, 1, 2])
        self.assertSequenceEqual(l0.words, (t1, t3))


class Layer1Tests(unittest.TestCase):
    """Tests layer1 module functionality and correctness."""

    @staticmethod
    def _create_passage():
        """Creates a Passage to work with using layer1 objects.

        Annotation layout (what annotation each terminal has):
            1: Linker, linked with the first parallel scene
            2-10: Parallel scene #1, 2-5 ==> Participant #1
                6-9 ==> Process #1, 10 ==> Punctuation, remote Participant is
                Adverbial #2
            11-19: Parallel scene #23, which encapsulated 2 scenes and a linker
                (not a real scene, has no process, only for grouping)
            11-15: Parallel scene #2 (under #23), 11-14 ==> Participant #3,
                15 ==> Adverbial #2, remote Process is Process #1
            16: Linker #2, links Parallel scenes #2 and #3
            17-19: Parallel scene #3, 17-18 ==> Process #3,
                19 ==> Participant #3, implicit Pariticpant
            20: Punctuation (under the head)

        """

        p = core.Passage('1')
        l0 = layer0.Layer0(p)
        l1 = layer1.Layer1(p)
        # 20 terminals (1-20), #10 and #20 are punctuation
        terms = [l0.add_terminal(text=str(i), punct=(i % 10 == 0))
                 for i in range(1, 21)]

        # Linker #1 with terminal 1
        link1 = l1.add_fnode(None, layer1.EdgeTags.Linker)
        link1.add(layer1.EdgeTags.Terminal, terms[0])

        # Scene #1: [[2 3 4 5 P] [6 7 8 9 A] [10 U] H]
        ps1 = l1.add_fnode(None, layer1.EdgeTags.ParallelScene)
        p1 = l1.add_fnode(ps1, layer1.EdgeTags.Process)
        a1 = l1.add_fnode(ps1, layer1.EdgeTags.Participant)
        p1.add(layer1.EdgeTags.Terminal, terms[1])
        p1.add(layer1.EdgeTags.Terminal, terms[2])
        p1.add(layer1.EdgeTags.Terminal, terms[3])
        p1.add(layer1.EdgeTags.Terminal, terms[4])
        a1.add(layer1.EdgeTags.Terminal, terms[5])
        a1.add(layer1.EdgeTags.Terminal, terms[6])
        a1.add(layer1.EdgeTags.Terminal, terms[7])
        a1.add(layer1.EdgeTags.Terminal, terms[8])
        l1.add_punct(ps1, terms[9])

        # Scene #23: [[11 12 13 14 15 H] [16 L] [17 18 19 H] H]
        # Scene #2: [[11 12 13 14 P] [15 D]]
        ps23 = l1.add_fnode(None, layer1.EdgeTags.ParallelScene)
        ps2 = l1.add_fnode(ps23, layer1.EdgeTags.ParallelScene)
        a2 = l1.add_fnode(ps2, layer1.EdgeTags.Participant)
        a2.add(layer1.EdgeTags.Terminal, terms[10])
        a2.add(layer1.EdgeTags.Terminal, terms[11])
        a2.add(layer1.EdgeTags.Terminal, terms[12])
        a2.add(layer1.EdgeTags.Terminal, terms[13])
        d2 = l1.add_fnode(ps2, layer1.EdgeTags.Adverbial)
        d2.add(layer1.EdgeTags.Terminal, terms[14])

        # Linker #2: [16 L]
        link2 = l1.add_fnode(ps23, layer1.EdgeTags.Linker)
        link2.add(layer1.EdgeTags.Terminal, terms[15])

        # Scene #3: [[16 17 S] [18 A] (implicit participant) H]
        ps3 = l1.add_fnode(ps23, layer1.EdgeTags.ParallelScene)
        p3 = l1.add_fnode(ps3, layer1.EdgeTags.State)
        p3.add(layer1.EdgeTags.Terminal, terms[16])
        p3.add(layer1.EdgeTags.Terminal, terms[17])
        a3 = l1.add_fnode(ps3, layer1.EdgeTags.Participant)
        a3.add(layer1.EdgeTags.Terminal, terms[18])
        a4 = l1.add_fnode(ps3, layer1.EdgeTags.Participant, implicit=True)

        # Punctuation #20 - not under a scene
        l1.add_punct(None, terms[19])

        # adding remote argument to scene #1, remote process to scene #2
        # creating linkages L1->H1, H2<-L2->H3
        l1.add_remote(ps1, layer1.EdgeTags.Participant, d2)
        l1.add_remote(ps2, layer1.EdgeTags.Process, p1)
        l1.add_linkage(link1, ps1)
        l1.add_linkage(link2, ps2, ps3)

        return p

    def test_creation(self):
        p = self._create_passage()
        head = p.layer('1').heads[0]
        self.assertSequenceEqual([x.tag for x in head], ['L', 'H', 'H', 'U'])
        self.assertSequenceEqual([x.child.position for x in head[0].child],
                                 [1])
        self.assertSequenceEqual([x.tag for x in head[1].child],
                                 ['P', 'A', 'U', 'A'])
        self.assertSequenceEqual([x.child.position
                                  for x in head[1].child[0].child],
                                 [2, 3, 4, 5])
        self.assertSequenceEqual([x.child.position
                                  for x in head[1].child[1].child],
                                 [6, 7, 8, 9])
        self.assertSequenceEqual([x.child.position
                                  for x in head[1].child[2].child],
                                 [10])
        self.assertTrue(head[1].child[3].attrib.get('remote'))

    def test_fnodes(self):
        p = self._create_passage()
        l0 = p.layer('0')
        l1 = p.layer('1')

        terms = l0.all
        head, lkg1, lkg2 = l1.heads
        link1, ps1, ps23, punct2 = [x.child for x in head]
        p1, a1, punct1 = [x.child for x in ps1 if not x.attrib.get('remote')]
        ps2, link2, ps3 = [x.child for x in ps23]
        a2, d2 = [x.child for x in ps2 if not x.attrib.get('remote')]
        p3, a3, a4 = [x.child for x in ps3]

        self.assertEqual(lkg1.relation, link1)
        self.assertSequenceEqual(lkg1.arguments, [ps1])
        self.assertIsNone(ps23.process)
        self.assertEqual(ps2.process, p1)
        self.assertSequenceEqual(ps1.participants, [a1, d2])
        self.assertSequenceEqual(ps3.participants, [a3, a4])

        self.assertSequenceEqual(ps1.get_terminals(), terms[1:10])
        self.assertSequenceEqual(ps1.get_terminals(punct=False, remotes=True),
                                 terms[1:9] + terms[14:15])
        self.assertEqual(ps1.end_position, 10)
        self.assertEqual(ps2.start_position, 11)
        self.assertEqual(ps3.start_position, 17)
        self.assertEqual(a4.start_position, -1)
        self.assertEqual(ps23.to_text(), '11 12 13 14 15 16 17 18 19')

        self.assertEqual(ps1.fparent, head)
        self.assertEqual(link2.fparent, ps23)
        self.assertEqual(ps2.fparent, ps23)
        self.assertEqual(d2.fparent, ps2)

    def test_layer1(self):
        p = self._create_passage()
        l1 = p.layer('1')

        head, lkg1, lkg2 = l1.heads
        link1, ps1, ps23, punct2 = [x.child for x in head]
        p1, a1, punct1 = [x.child for x in ps1 if not x.attrib.get('remote')]
        ps2, link2, ps3 = [x.child for x in ps23]
        a2, d2 = [x.child for x in ps2 if not x.attrib.get('remote')]
        p3, a3, a4 = [x.child for x in ps3]

        self.assertSequenceEqual(l1.top_scenes, [ps1, ps2, ps3])
        self.assertSequenceEqual(l1.top_linkages, [lkg1, lkg2])

        # adding scene #23 to linkage #1, which makes it non top-level as
        # scene #23 isn't top level
        lkg1.add(layer1.EdgeTags.LinkArgument, ps23)
        self.assertSequenceEqual(l1.top_linkages, [lkg2])

        # adding process to scene #23, which makes it top level and discards
        # "top-levelness" from scenes #2 + #3
        l1.add_remote(ps23, layer1.EdgeTags.Process, p1)
        self.assertSequenceEqual(l1.top_scenes, [ps1, ps23])
        self.assertSequenceEqual(l1.top_linkages, [lkg1, lkg2])


class ConversionTests(unittest.TestCase):
    """Tests convert module correctness and API."""

    @staticmethod
    def _load_xml(path):
        """XML file path ==> root element"""
        with open(path) as f:
            return ETree.ElementTree().parse(f)

    def _test_edges(self, node, tags):
        """Tests that the node edge tags and number match tags argument."""
        self.assertEqual(len(node), len(tags))
        for edge, tag in zip(node, tags):
            self.assertEqual(edge.tag, tag)

    def _test_terms(self, node, terms):
        """Tests that node contain the terms given, and only them."""
        for edge, term in zip(node, terms):
            self.assertEqual(edge.tag, layer1.EdgeTags.Terminal)
            self.assertEqual(edge.child, term)

    def test_site_terminals(self):
        elem = self._load_xml('./site1.xml')
        passage = convert.from_site(elem)
        terms = passage.layer(layer0.LAYER_ID).all

        self.assertEqual(passage.ID, '118')
        self.assertEqual(len(terms), 15)

        # There are two punctuation signs (dots, positions 5 and 11), which
        # also serve as paragraph end points. All others are words whose text
        # is their positions, so test that both text, punctuation (yes/no)
        # and paragraphs are converted correctly
        for i, t in enumerate(terms):
            # i starts in 0, positions at 1, hence 5,11 ==> 4,10
            if i in (4, 10):
                self.assertTrue(t.text == '.' and t.punct is True)
            else:
                self.assertTrue(t.text == str(i + 1) and t.punct is False)
            if i < 5:
                par = 1
            elif i < 11:
                par = 2
            else:
                par = 3
            self.assertEqual(t.paragraph, par)

    def test_site_simple(self):
        elem = self._load_xml('./site2.xml')
        passage = convert.from_site(elem)
        terms = passage.layer(layer0.LAYER_ID).all
        l1 = passage.layer('1')

        # The Terminals in the passage are just like in test_site_terminals,
        # with this layer1 heirarchy: [[1 C] [2 E] L] [3 4 . H]
        # with the linker having a remark and the parallel scene is uncertain
        head = l1.heads[0]
        self.assertEqual(len(head), 12)  # including all 'unused' terminals
        self.assertEqual(head[9].tag, layer1.EdgeTags.Linker)
        self.assertEqual(head[10].tag, layer1.EdgeTags.ParallelScene)
        linker = head[9].child
        self._test_edges(linker, [layer1.EdgeTags.Center,
                                  layer1.EdgeTags.Elaborator])
        self.assertTrue(linker.extra['remarks'], '"remark"')
        center = linker[0].child
        elab = linker[1].child
        self._test_terms(center, terms[0:1])
        self._test_terms(elab, terms[1:2])
        ps = head[10].child
        self._test_edges(ps, [layer1.EdgeTags.Terminal,
                              layer1.EdgeTags.Terminal,
                              layer1.EdgeTags.Punctuation])
        self.assertTrue(ps.attrib.get('uncertain'))
        self.assertEqual(ps[0].child, terms[2])
        self.assertEqual(ps[1].child, terms[3])
        self.assertEqual(ps[1].child, terms[3])
        self.assertEqual(ps[2].child[0].child, terms[4])

    def test_site_advanced(self):
        elem = self._load_xml('./site3.xml')
        passage = convert.from_site(elem)
        terms = passage.layer(layer0.LAYER_ID).all
        l1 = passage.layer('1')

        # This passage has the same terminals as the simple and terminals test,
        # and have the same layer1 units for the first paragraph as the simple
        # test. In addition, it has the following annotation:
        # [6 7 8 9 H] [10 F] .
        # the 6-9 H has remote D which is [10 F]. Inside of 6-9, we have [8 S]
        # and [6 7 .. 9 A], where [6 E] and [7 .. 9 C].
        # [12 H] [13 H] [14 H] [15 L], where 15 linkage links 12, 13 and 14 and
        # [15 L] has an implicit Center unit
        head, lkg = l1.heads
        self._test_edges(head, [layer1.EdgeTags.Linker,
                                layer1.EdgeTags.ParallelScene,
                                layer1.EdgeTags.ParallelScene,
                                layer1.EdgeTags.Function,
                                layer1.EdgeTags.Punctuation,
                                layer1.EdgeTags.ParallelScene,
                                layer1.EdgeTags.ParallelScene,
                                layer1.EdgeTags.ParallelScene,
                                layer1.EdgeTags.Linker])

        # we only take what we haven't checked already
        ps1, func, punct, ps2, ps3, ps4, link = [x.child for x in head[2:]]
        self._test_edges(ps1, [layer1.EdgeTags.Participant,
                               layer1.EdgeTags.Process,
                               layer1.EdgeTags.Adverbial])
        self.assertTrue(ps1[2].attrib.get('remote'))
        ps1_a, ps1_p, ps1_d = [x.child for x in ps1]
        self._test_edges(ps1_a, [layer1.EdgeTags.Elaborator,
                                 layer1.EdgeTags.Center])
        self._test_terms(ps1_a[0].child, terms[5:6])
        self._test_terms(ps1_a[1].child, terms[6:9:2])
        self._test_terms(ps1_p, terms[7:8])
        self.assertEqual(ps1_d, func)
        self._test_terms(func, terms[9:10])
        self._test_terms(punct, terms[10:11])
        self._test_terms(ps2, terms[11:12])
        self._test_terms(ps3, terms[12:13])
        self._test_terms(ps4, terms[13:14])
        self.assertEqual(len(link), 2)
        self.assertEqual(link[0].tag, layer1.EdgeTags.Terminal)
        self.assertEqual(link[0].child, terms[14])
        self.assertEqual(link[1].tag, layer1.EdgeTags.Center)
        self.assertTrue(link[1].child.attrib.get('implicit'))
        self.assertEqual(lkg.relation, link)
        self.assertSequenceEqual(lkg.arguments, [ps2, ps3, ps4])